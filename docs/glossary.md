---
icon: material/book-alphabet
---

# Glossary

Key terms used in Matyan documentation. Each links to the canonical definition or reference.

| Term | Definition | See |
|------|------------|-----|
| **Run** | One experiment/training run; the main object for tracking metrics and params. | [Concepts — Run](understanding/concepts.md#run) |
| **Repo** | The set of all runs served by one backend; in code, the `Repo` handle to the backend. | [Concepts — Repo](understanding/concepts.md#repo-backend) |
| **Sequence** | An ordered list of values of the same kind (e.g. a metric series), bound to a run and identified by name and context. | [Concepts — Run sequence](understanding/concepts.md#run-sequence) |
| **Context** | A dict that distinguishes multiple sequences with the same name in one run (e.g. train vs val). | [Concepts — Sequence context](understanding/concepts.md#sequence-context) |
| **MatyanQL** | The query language for filtering runs, metrics, and custom objects in the UI and API. | [Search and MatyanQL](understanding/search-and-matyanql.md) |
