# Concepts: HyperAgents → Layerd AI Agent Reforge

This document maps ideas described in Meta’s [HyperAgents](https://ai.meta.com/research/publications/hyperagents/) (DGM-H) to **Layerd AI Agent Reforge** modules. It is an independent implementation inspired by that research, not Meta’s code.

| HyperAgents idea (from publication summary) | Reforge module / type |
|-----------------------------------------------|------------------------|
| Task agent + improvement-side agent in one editable program | `UnifiedProgram`, `TaskAgentSpec`, `ReforgeAgentSpec` |
| Improvement procedure that evolves agents is itself editable | `ReforgeProcedureSpec`, `ReforgeProcedureEngine`, `ReforgeNestedProcedureConfig` |
| Variant generation and evaluation | `VariantGenerator`, `ImprovementLoop`, `Evaluator` |
| Archive of stepping stones | `ArchiveEntry`, `ArchiveStore`, `SqliteArchiveStore` |
| Lineage and retrieval for future improvement | `ArchiveStore.lineage`, `retrieve_for_reforge_context` |
| Sandboxing and resource limits | `SandboxRunner`, `SubprocessSandboxBackend` |
| Human oversight | `HumanGate`, `AuditLogStore` |
| Persistent memory / performance tracking | `RunLedger`, `ReforgeMemory` (archive + pipeline steps) |
| Cross-domain transfer hooks | `DomainTag`, `TransferPolicy`, `examples/cross_domain_transfer.py` |
| Complements task runtime (e.g. LangGraph) | `adapters/langgraph.py`, `ProgramMaterializer` |
