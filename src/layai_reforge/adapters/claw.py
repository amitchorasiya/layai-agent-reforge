"""
OpenClaw / NemoClaw CLI integration.

OpenClaw exposes a Node CLI; typical eval run::

    openclaw agent --message "..." --thinking high

NVIDIA NemoClaw (or other wrappers) can be used by setting ``executable`` and
``subcommand`` on :class:`ClawRuntimeConfig` if the CLI surface matches.

See https://github.com/openclaw/openclaw and https://docs.openclaw.ai
"""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field

from layai_reforge.models.artifacts import RunArtifact
from layai_reforge.models.program import TaskAgentSpec, UnifiedProgram, Variant
from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


class ClawRuntimeConfig(BaseModel):
    """Maps Reforge ``TaskAgentSpec.graph_config["claw"]`` + overrides to argv."""

    executable: str = Field(
        default="openclaw",
        description="Binary on PATH (e.g. openclaw) or absolute path (NemoClaw: nemoclaw if compatible).",
    )
    subcommand: list[str] = Field(
        default_factory=lambda: ["agent"],
        description="Tokens after executable (default: one-shot agent run).",
    )
    message_flag: str = "--message"
    extra_args: list[str] = Field(
        default_factory=list,
        description="Appended after --message <payload> (e.g. --json for machine-readable output if supported).",
    )
    thinking: str | None = Field(
        default=None,
        description="If set, inserts --thinking <value> before extra_args (OpenClaw: low|medium|high).",
    )
    prepend_system_prompt: bool = True
    system_prompt_header: str = "### Reforge system instructions"
    task_header: str = "### Task"
    append_tool_descriptors: bool = True
    cwd: Path | None = Field(
        default=None,
        description="Working directory for the CLI; defaults to sandbox workspace_root.",
    )


def merge_claw_config(
    task: TaskAgentSpec,
    override: ClawRuntimeConfig | None = None,
) -> ClawRuntimeConfig:
    raw = (task.graph_config or {}).get("claw")
    base = ClawRuntimeConfig()
    if isinstance(raw, dict):
        merged = {**base.model_dump(), **raw}
        base = ClawRuntimeConfig.model_validate(merged)
    if override is not None:
        patch = override.model_dump(exclude_none=True)
        base = base.model_copy(update=patch)
    return base


def compose_claw_message(task: TaskAgentSpec, user_message: str, cfg: ClawRuntimeConfig) -> str:
    parts: list[str] = []
    if cfg.prepend_system_prompt and task.system_prompt.strip():
        parts.append(f"{cfg.system_prompt_header}\n{task.system_prompt.strip()}")
    parts.append(f"{cfg.task_header}\n{user_message.strip()}")
    if cfg.append_tool_descriptors and task.tools:
        lines = "\n".join(
            f"- **{t.name}**" + (f": {t.description}" if t.description else "")
            for t in task.tools
        )
        parts.append(f"### Documented tools (for agent context)\n{lines}")
    return "\n\n".join(parts)


def build_claw_argv(cfg: ClawRuntimeConfig, message: str) -> list[str]:
    argv: list[str] = [cfg.executable, *cfg.subcommand, cfg.message_flag, message]
    if cfg.thinking is not None:
        argv.extend(["--thinking", cfg.thinking])
    argv.extend(cfg.extra_args)
    return argv


def sandbox_config_allow_claw(base: SandboxConfig) -> SandboxConfig:
    """Allow OpenClaw / common Node launchers in addition to existing allowlist."""
    extra = ("openclaw", "nemoclaw", "npx", "pnpm", "bun", "node")
    seen: dict[str, None] = {}
    for n in [*base.allowed_executable_basenames, *extra]:
        seen.setdefault(n, None)
    return base.model_copy(update={"allowed_executable_basenames": list(seen.keys())})


def run_claw_agent_task(
    runner: SandboxRunner,
    task: TaskAgentSpec,
    user_message: str,
    *,
    variant_id: str | None = None,
    claw_config: ClawRuntimeConfig | None = None,
    extra_env: dict[str, str] | None = None,
) -> RunArtifact:
    """
    Run ``openclaw agent --message ...`` (or equivalent) inside sandbox rules.

    **Network:** OpenClaw usually needs outbound access to models; set
    ``SandboxConfig(allow_network=True)`` (and env_allowlist as needed) for real runs.
    """
    cfg = merge_claw_config(task, claw_config)
    payload = compose_claw_message(task, user_message, cfg)
    argv = build_claw_argv(cfg, payload)
    cwd = cfg.cwd if cfg.cwd is not None else runner.config.workspace_root
    claw_runner = SandboxRunner(
        sandbox_config_allow_claw(runner.config),
        backend=runner.backend,
    )
    return claw_runner.run_command(argv, cwd=cwd, variant_id=variant_id, extra_env=extra_env)


def run_claw_agent_for_program(
    runner: SandboxRunner,
    program: UnifiedProgram,
    variant: Variant,
    user_message: str,
    claw_config: ClawRuntimeConfig | None = None,
    extra_env: dict[str, str] | None = None,
) -> RunArtifact:
    """Convenience for ImprovementLoop: uses ``program.task`` and ``variant.id``."""
    return run_claw_agent_task(
        runner,
        program.task,
        user_message,
        variant_id=variant.id,
        claw_config=claw_config,
        extra_env=extra_env,
    )
