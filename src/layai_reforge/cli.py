"""CLI entrypoint: layai-reforge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from layai_reforge.archive.merge import read_bundle, write_bundle
from layai_reforge.archive.sqlite_store import SqliteArchiveStore
from layai_reforge.models.program import TaskAgentSpec, UnifiedProgram
from layai_reforge.program_io import load_program, save_program


def cmd_init(args: argparse.Namespace) -> int:
    p = Path(args.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    program = UnifiedProgram(task=TaskAgentSpec(system_prompt="You are an agent."))
    save_program(program, p)
    print("Wrote", p)
    return 0


def cmd_archive_list(args: argparse.Namespace) -> int:
    store = SqliteArchiveStore(args.db)
    for e in store.list_entries(limit=args.limit):
        print(e.id, e.domain.value, e.fingerprint[:12], e.scores)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = SqliteArchiveStore(args.db)
    write_bundle(Path(args.out), store, limit=args.limit)
    print("Exported to", args.out)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    store = SqliteArchiveStore(args.db)
    from layai_reforge.archive.merge import merge_archives

    incoming = read_bundle(Path(args.path))
    n = merge_archives(store, incoming)
    print("Imported", n, "entries")
    return 0


def cmd_eval_once(args: argparse.Namespace) -> int:
    """Load program JSON/YAML and print fingerprint (placeholder eval hook)."""
    prog = load_program(args.program)
    print(json.dumps({"fingerprint": prog.content_fingerprint(), "id": prog.id}, indent=2))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    print("Promotion is application-specific; use ImprovementLoop + HumanGate in Python API.")
    return 0


def cmd_run_loop(args: argparse.Namespace) -> int:
    print("run-loop: use examples/minimal_loop.py or ReforgeSession.run_improvement_generation")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    print("replay: re-run evaluator on stored RunArtifact JSON (integrate with your telemetry).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="layai-reforge",
        description="Layerd AI Agent Reforge — outer-loop agent improvement CLI.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create starter program YAML/JSON")
    p_init.add_argument("path", type=str)
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser("archive-list", help="List archive entries")
    p_list.add_argument("--db", type=str, required=True)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_archive_list)

    p_exp = sub.add_parser("export", help="Export archive bundle JSON")
    p_exp.add_argument("--db", type=str, required=True)
    p_exp.add_argument("--out", type=str, required=True)
    p_exp.add_argument("--limit", type=int, default=10_000)
    p_exp.set_defaults(func=cmd_export)

    p_imp = sub.add_parser("import", help="Import archive bundle JSON")
    p_imp.add_argument("--db", type=str, required=True)
    p_imp.add_argument("path", type=str)
    p_imp.set_defaults(func=cmd_import)

    p_ev = sub.add_parser("eval-once", help="Load program and print fingerprint")
    p_ev.add_argument("program", type=str)
    p_ev.set_defaults(func=cmd_eval_once)

    sub.add_parser("promote", help="Promotion docs").set_defaults(func=cmd_promote)
    sub.add_parser("run-loop", help="Outer loop docs").set_defaults(func=cmd_run_loop)
    sub.add_parser("replay", help="Replay docs").set_defaults(func=cmd_replay)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
