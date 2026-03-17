---
icon: material/hand-coin-outline
---

# Contributing to Matyan

Contributions are welcome. For large changes, open an issue first to align on design.

## Where to open issues and pull requests

**Open issues and pull requests in the repository that owns the code you are changing.** Do not open component-specific issues or PRs in this (core) repo unless they belong here.

- **This repo (matyan-core)** — Use **only** for:
  - **Helm charts** (e.g. `deploy/helm/`)
  - **Documentation** (e.g. `docs/`, `mkdocs.yml`)
  - **Integration tests** (e.g. tests that span backend, frontier, client, or infrastructure)

- **Other / component repos** — Use for all other issues and PRs (e.g. backend, frontier, client, UI, or API models). Open issues and PRs in the respective repo that contains the code you want to change or discuss.

## How you can contribute

- Review [pull requests](https://github.com/4gt-104/matyan-core/pulls) (in this repo or the relevant component repo)
- [Open an issue](https://github.com/4gt-104/matyan-core/issues/new) in the right repo to report bugs or suggest features
- Submit a pull request with a new feature or fix in the repo that owns the changed code

See the repository for development setup and testing. Code style (type hints, Ruff, ty, test coverage, and stub files) is documented in [Code style](contributing/code-style.md). For unit vs integration tests and how to run integration tests (with Docker), see [Testing](contributing/testing.md).

## Publishing the documentation

The docs are built with MkDocs and published to [https://4gt-104.github.io/matyan-core/](https://4gt-104.github.io/matyan-core/) via the `gh-pages` submodule (repo [4gt-104.github.io](https://github.com/4gt-104/4gt-104.github.io)). To update the live site:

1. Ensure the `gh-pages` submodule is initialized (`git submodule update --init gh-pages`). If the Pages repo is empty, create an initial commit there first (e.g. add a README and push).
2. Run from the repo root: `./scripts/publish-docs-to-gh-pages.sh`
3. In `gh-pages`: `git add matyan-core`, commit, and push.
