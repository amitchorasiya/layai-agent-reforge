# Layerd AI Agent Reforge — project context

**Last updated:** 2026-03-29

## What this is

**Layerd AI Agent Reforge** (`pip install layai-agent-reforge`, import `layai_reforge`) is a Python **outer-loop** framework for **self-improving agents**: variant generation, sandboxed runs, evaluation, archives, human promotion gates, and an editable **reforge procedure**. It is meant to **complement [LangGraph](https://github.com/langchain-ai/langgraph)** (or similar runtimes)—the compiled graph stays the task executor; **Reforge** evolves the **unified program** (prompts, tools, graph config) via measured improvement loops.

Concepts are **inspired by** Meta’s [HyperAgents](https://ai.meta.com/research/publications/hyperagents/) research; this code is **not** Meta’s and is **not affiliated with Meta**.

**Naming:** full product name **Layerd AI Agent Reforge**; short form **Reforge**. PyPI distribution **`layai-agent-reforge`**; import namespace **`layai_reforge`**.

## Package layout

| Path | Role |
|------|------|
| `src/layai_reforge/` | Installable package (`layai_reforge`) |
| `src/layai_reforge/loop/` | `ImprovementLoop`, `PromotionPolicy`, `VariantGenerator`, budgets |
| `src/layai_reforge/archive/` | `SqliteArchiveStore`, merge, optional Postgres extra |
| `src/layai_reforge/sandbox/` | `SandboxRunner`, subprocess backend |
| `src/layai_reforge/evaluators/` | Registry, composite, math/coding/paper/robotics examples |
| `src/layai_reforge/gates/` | `HumanGate`, audit |
| `src/layai_reforge/reforge/` | `ReforgeProcedureEngine`, `ReforgeContext` |
| `src/layai_reforge/adapters/` | `langgraph`, `materializer`, `claw` (OpenClaw / NemoClaw-style CLI argv) |
| `docs/concepts.md` | HyperAgents ideas → modules |
| `examples/` | `minimal_loop.py`, `cross_domain_transfer.py`, `hypothetical_status_agent.py` (E2E-style stub: health-check prompt variants → `MathGradingEvaluator`); `examples/__init__.py` makes the package importable from tests |
| `tests/` | `pytest` suite; `conftest.py` prepends `src/` and repo root to `sys.path` (imports `layai_reforge` and `examples.*`) |
| `tests/test_hypothetical_status_agent.py` | Integration test for the hypothetical scenario (`run_status_agent_demo`) |
| `tests/test_reforge_engine.py` | `ReforgeProcedureEngine` retrieve step smoke test |

CLI entrypoint: **`layai-reforge`** (`layai_reforge.cli:main`).

## Development

```bash
cd layai-agent-reforge   # repo root after you move this folder out
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Optional: `pip install -e ".[langgraph]"` or `.[postgres]` as needed.

## Publishing (checklist)

When this tree is its **own Git repo**:

1. **LICENSE:** repo includes MIT `LICENSE` at root; update copyright year/holder if your legal process requires it.
2. Set **`[project.urls]`** in `pyproject.toml` to the real GitHub (or GitLab) URLs instead of `example/layai-agent-reforge`.
3. Tag releases (e.g. `v0.1.0`) and build: `python -m build` (install `build` tool) or `hatch build`.
4. **PyPI:** use `twine upload dist/*` (or trusted publishing) with API tokens.
5. Confirm **sdist/wheel** include intended files (`pyproject.toml` controls `hatch` includes).

## Integration notes

- **Promotion** does not auto-deploy: `ImprovementLoopResult.promoted_program` is a snapshot; your app persists or rolls it out.
- **`HumanGate`:** use in production before treating a variant as canonical.
- **Claw adapter:** `layai_reforge.adapters.claw` — `ClawRuntimeConfig`, `graph_config["claw"]`; executable may be `openclaw`, `nemoclaw`, or a path.
- **LangGraph:** optional extra; see `adapters/langgraph.py` and `ProgramMaterializer`.
- **Demo UI:** not in this repo; outer loop is exercised via scripts and pytest. A thin web UI (e.g. FastAPI/Streamlit) would sit on top of `HumanGate` + `ImprovementLoop` if needed for stakeholders.

## Hypothetical end-to-end example

`examples/hypothetical_status_agent.py` implements a **deployment health-check** toy: `run_artifact_fn` simulates execution by reading `system_prompt` (no LLM). Two variants (paraphrase vs explicit “print exactly … HEALTH_OK” contract); the contract variant scores highest and is promoted. Run: `python examples/hypothetical_status_agent.py` from repo root (script bootstraps `src/` onto `sys.path` if needed) or use `pip install -e .` and import `run_status_agent_demo`.

## When resuming work

1. Read `README.md` and `docs/concepts.md`.
2. Run `pytest` after `pip install -e ".[dev]"` (includes `test_hypothetical_status_agent.py`, `test_reforge_engine.py`).
3. For behavior changes, extend tests under `tests/` and run the full suite.
4. To sanity-check the outer loop manually: `python examples/hypothetical_status_agent.py` or `examples/minimal_loop.py`.
