---
icon: material/code-braces
---

# Code style

This page describes the code style and tooling expectations for the Matyan codebase: test coverage, type hints, handling of `Any`, stub files for untyped dependencies, and the use of **Ruff** and **ty**.

## High test coverage

- New code should be accompanied by tests. The project aims for **high test coverage** so that refactors and fixes are safe.
- **matyan-backend** and **matyan-client** use **pytest** with **pytest-cov** for coverage. Run tests with coverage from each package directory, for example:
  - `cd extra/matyan-backend && uv run pytest --cov=matyan_backend --cov-report=term-missing`
  - `cd extra/matyan-client && uv run pytest --cov=matyan_client --cov-report=term-missing`
- Prefer small, focused tests. Use fixtures and parametrization where it improves clarity. Cover both success and expected failure paths where relevant.

## Type hinting

- Use **type hints** on public APIs and on new or modified code (parameters, return types, and important locals where it helps).
- Prefer modern syntax: `list[str]`, `dict[str, int]`, `X | None` (Python 3.10+). Use `from __future__ import annotations` at the top of the file when you need forward references or to avoid runtime cost of evaluating annotations.
- The codebase is type-checked with **ty**. Run `uvx ty check` (or `uvx ty check src/`) from the repo root or from the package you are changing. Fix type errors before submitting.

## `Any` and annotation warnings (ANN401)

- **Avoid `Any`** wherever a more precise type is possible. It opts out of type safety and is flagged by Ruff rule **ANN401**.
- When `Any` is **genuinely unavoidable** (e.g. generic serialization boundaries, FDB transaction arguments whose type is opaque, or third-party APIs that are untyped), add **`# noqa: ANN401`** on the offending line to suppress the warning. Prefer a short comment explaining why (e.g. “FDB key type is opaque”).
- Do not use `Any` as a shortcut to silence the type checker; prefer `Protocol`, `TypeVar`, or a small stub (see below) when you can describe the shape of the value.

## Stub files and untyped dependencies

- Many dependencies (e.g. **foundationdb**) do not ship with **PEP 561** `py.typed` or `.pyi` stub files. Type checkers then treat their APIs as untyped, which leads to `Any` or false positives.
- **When you introduce or rely on an untyped package**, consider adding type information alongside your changes:
  - **In-repo stubs** — Add a **`.pyi` stub file** in your package (e.g. under `src/` or a `stubs/` directory) that declares the classes and functions you use. Name it so the type checker can find it (e.g. for a package `foo`, a stub package `foo-stubs` or a local `foo.pyi` in a path that ty/mypy is configured to read).
  - **Wrapper module** — Alternatively, create a small **wrapper or protocol module** in your codebase that re-exports or defines `Protocol`/`TypedDict` for the subset of the dependency you use. The backend does this for FoundationDB in **`matyan_backend.fdb_types`**: it re-exports the concrete FDB classes and defines `Protocol` types for duck-typed objects (e.g. `Transaction`, key-value results) so the rest of the code can be fully typed without waiting for upstream stubs.
- Prefer **contributing stubs upstream** (e.g. to [typeshed](https://github.com/python/typeshed) or the project’s repo) when the API is stable and the maintenance burden is acceptable. Until then, in-repo stubs or a local `fdb_types`-style module keep the codebase strict and documented.

## Ruff (lint and format)

- **Ruff** is the project’s **linter and formatter**. It is run via **uvx** (not installed in the project env):
  - **Lint:** `uvx ruff check .` (use `--fix` to auto-fix where safe).
  - **Format:** `uvx ruff format .`
- Run these from the repo root or from the package directory you changed. CI or pre-commit should enforce them; fix lint and format issues before submitting.
- Other Ruff rules are enabled; add `# noqa: <code>` only when necessary, with a brief comment if the reason is non-obvious.

## ty (type checker)

- **ty** is the project’s **type checker**. Run it with **uvx**:
  - `uvx ty check`
  - Or with an explicit path: `uvx ty check src/`
- Do not rely on `mypy` or another checker unless the project is explicitly configured for it; use **`uvx ty check`** so the same tool and configuration are used everywhere.
- Fix all reported type errors in the code you change. If you need to suppress a single line (e.g. for an untyped third-party call), use a targeted `# type: ignore[<code>]` that follows **ty**’s rules (not mypy or other type-checker syntax), with a short comment, and prefer improving stubs or types so that the ignore can be removed later.

## Docstrings

- All docstrings must be written in **Sphinx format** (reStructuredText with `:param`, `:returns`, `:raises`, etc.) so that mkdocstrings and the API reference render them correctly. **Omit** `:type` and `:rtype` — the code is already type-hinted; do not duplicate types in the docstring.
- **Every** public **function**, **class**, **method**, **property**, and **module** must have a **verbose docstring**: a short imperative summary, then parameters, return value, raised exceptions, and (when useful) a brief body explaining behavior or usage.
- Avoid minimal or placeholder docstrings; prefer a clear description of what the API does and when to use it. See the project’s docstring conventions in `.cursor/rules/docstrings.mdc` for examples.

## Summary

| Area | Expectation |
|------|-------------|
| **Tests** | High coverage; pytest + pytest-cov; tests for new and modified code. |
| **Docstrings** | Sphinx format; verbose docstrings for all public functions, classes, methods, properties, and modules. |
| **Types** | Type hints on public APIs and new code; run `uvx ty check`. |
| **`Any`** | Avoid; use `# noqa: ANN401` only when necessary, with a brief justification. |
| **Untyped deps** | Prefer adding `.pyi` stubs or a small typed wrapper (e.g. `fdb_types`) alongside your changes. |
| **Ruff** | `uvx ruff check .` and `uvx ruff format .`; fix issues; I001/I002 and F401 (re-exports) are exempt. |
| **ty** | `uvx ty check`; fix type errors; use targeted `# type: ignore` only when needed. |

These conventions keep the codebase consistent, type-safe, and easy to refactor. When in doubt, match existing patterns in the package you are editing (e.g. `matyan_backend.fdb_types` for FDB, or the use of `noqa: ANN401` in serialization helpers).
