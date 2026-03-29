"""Integration test for examples/hypothetical_status_agent.py (deployment health stub)."""

import tempfile
from pathlib import Path

from examples.hypothetical_status_agent import run_status_agent_demo


def test_health_agent_promotes_contract_variant():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        res = run_status_agent_demo(root)
        assert res.promoted_program is not None
        assert "HEALTH_OK" in res.promoted_program.task.system_prompt
        assert "exactly" in res.promoted_program.task.system_prompt.lower()
        assert len(res.archive_entry_ids) == 2
        assert len(res.reports) == 2
