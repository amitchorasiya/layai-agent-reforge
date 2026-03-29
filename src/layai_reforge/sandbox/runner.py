"""Sandboxed execution: subprocess (default), optional Docker."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, Field

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.sandbox.redaction import redact_secrets


class SandboxConfig(BaseModel):
    workspace_root: Path
    wall_clock_seconds: float = Field(default=120.0, ge=1.0)
    allow_network: bool = False
    env_allowlist: list[str] = Field(default_factory=list)
    allowed_executable_basenames: list[str] = Field(
        default_factory=lambda: ["python", "python3", "pytest", "bash", "sh"]
    )


def _reject_path_traversal(workspace: Path, candidate: Path) -> Path:
    try:
        resolved = candidate.resolve()
        root = workspace.resolve()
        resolved.relative_to(root)
    except ValueError as e:
        raise ValueError("path escapes workspace") from e
    return resolved


class SandboxBackend(ABC):
    @abstractmethod
    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        pass


class SubprocessSandboxBackend(SandboxBackend):
    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


class DockerSandboxBackend(SandboxBackend):
    """Optional: run argv inside a container with workspace mounted at /work."""

    def __init__(self, image: str = "python:3.12-slim") -> None:
        self.image = image
        if not shutil.which("docker"):
            raise RuntimeError("docker CLI not found; install Docker or use SubprocessSandboxBackend")

    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        inner = " ".join(_shell_quote(a) for a in argv)
        docker_argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{cwd.resolve()}:/work",
            "-w",
            "/work",
            self.image,
            "sh",
            "-c",
            inner,
        ]
        return subprocess.run(
            docker_argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


def _shell_quote(s: str) -> str:
    if not s:
        return "''"
    if all(c.isalnum() or c in "/._-:" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


class SandboxRunner:
    def __init__(
        self,
        config: SandboxConfig,
        backend: SandboxBackend | None = None,
    ) -> None:
        self.config = config
        self.backend = backend or SubprocessSandboxBackend()

    def validate_executable(self, argv0: str) -> None:
        base = Path(argv0).name
        if base not in self.config.allowed_executable_basenames:
            raise ValueError(f"executable not allowlisted: {base}")

    def run_command(
        self,
        argv: Sequence[str],
        cwd: Path | None = None,
        variant_id: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> RunArtifact:
        if not argv:
            raise ValueError("argv empty")
        ws = self.config.workspace_root
        run_cwd = _reject_path_traversal(ws, (cwd or ws))
        self.validate_executable(argv[0])

        run_id = str(uuid.uuid4())
        env = os.environ.copy() if self.config.allow_network else {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "TZ")}
        if not self.config.allow_network:
            env.pop("HTTP_PROXY", None)
            env.pop("HTTPS_PROXY", None)
        for k in self.config.env_allowlist:
            if k in os.environ:
                env[k] = os.environ[k]
        if extra_env:
            env.update(extra_env)

        start = time.perf_counter()
        try:
            proc = self.backend.run(argv, run_cwd, env, self.config.wall_clock_seconds)
            latency_ms = (time.perf_counter() - start) * 1000
            return RunArtifact(
                run_id=run_id,
                variant_id=variant_id,
                stdout=redact_secrets(proc.stdout or ""),
                stderr=redact_secrets(proc.stderr or ""),
                exit_code=proc.returncode,
                success=proc.returncode == 0,
                latency_ms=latency_ms,
            )
        except subprocess.TimeoutExpired as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return RunArtifact(
                run_id=run_id,
                variant_id=variant_id,
                stdout=redact_secrets(e.stdout.decode() if e.stdout else ""),
                stderr=redact_secrets(e.stderr.decode() if e.stderr else "timeout"),
                exit_code=-1,
                success=False,
                latency_ms=latency_ms,
            )
