from pathlib import Path

import pytest

from layai_reforge.sandbox.runner import SandboxConfig, SandboxRunner


def test_path_traversal_rejected(tmp_path):
    runner = SandboxRunner(SandboxConfig(workspace_root=tmp_path))
    with pytest.raises(ValueError, match="escapes"):
        runner.run_command(["python3", "-c", "print(1)"], cwd=Path("/"))


def test_run_python_in_workspace(tmp_path):
    runner = SandboxRunner(SandboxConfig(workspace_root=tmp_path))
    art = runner.run_command(["python3", "-c", "print('ok')"], cwd=tmp_path)
    assert art.success
    assert "ok" in art.stdout
