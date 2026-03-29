import tempfile
from pathlib import Path

from layai_reforge import ArchiveEntry, DomainTag, SqliteArchiveStore, UnifiedProgram
from layai_reforge.models.program import TaskAgentSpec
from layai_reforge.archive.merge import merge_archives, read_bundle, write_bundle


def test_dedupe_fingerprint():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "a.sqlite"
        store = SqliteArchiveStore(db)
        p = UnifiedProgram(task=TaskAgentSpec(system_prompt="x"))
        e = ArchiveEntry(program=p, scores={"s": 1.0}, domain=DomainTag.GENERAL)
        id1 = store.add_entry(e)
        id2 = store.add_entry(e)
        assert id1 == id2


def test_export_import_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        store = SqliteArchiveStore(td / "a.sqlite")
        p = UnifiedProgram(task=TaskAgentSpec(system_prompt="y"))
        store.add_entry(ArchiveEntry(program=p, scores={}, domain=DomainTag.CODING))
        path = td / "bundle.json"
        write_bundle(path, store)
        incoming = read_bundle(path)
        store2 = SqliteArchiveStore(td / "b.sqlite")
        n = merge_archives(store2, incoming)
        assert n == 1
