import os
import subprocess
import sys
from pathlib import Path


def test_cli_init(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "p.yaml"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(
        [sys.executable, "-m", "layai_reforge.cli", "init", str(out)],
        cwd=root,
        env=env,
    )
    assert out.exists()
