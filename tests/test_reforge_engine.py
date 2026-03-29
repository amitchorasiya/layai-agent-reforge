import tempfile
from pathlib import Path

from layai_reforge import SqliteArchiveStore, UnifiedProgram
from layai_reforge.memory.ledger import ReforgeMemory, RunLedger
from layai_reforge.models.program import ArchiveEntry, DomainTag, ReforgeProcedureSpec, ReforgeProcedureStep, TaskAgentSpec
from layai_reforge.reforge.engine import ReforgeContext, ReforgeProcedureEngine


def test_engine_retrieve_step():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        store = SqliteArchiveStore(root / "a.sqlite")
        base = UnifiedProgram(
            task=TaskAgentSpec(system_prompt="hello"),
            reforge_procedure=ReforgeProcedureSpec(
                steps=[ReforgeProcedureStep(type="retrieve_archive", params={"k": 3})]
            ),
        )
        store.add_entry(ArchiveEntry(program=base, scores={"aggregate": 0.9}, domain=DomainTag.GENERAL))
        ctx = ReforgeContext(base_program=base, archive=store, reforge_memory=ReforgeMemory(), ledger=RunLedger())
        engine = ReforgeProcedureEngine(propose_patch_fn=None)
        res = engine.run(ctx)
        assert "retrieve_archive" in "".join(res.logs)
