# Matyan Core

Monorepo for **Matyan** (մատյան, *book of records* in Armenian), an experiment-tracking stack forked from [Aim](https://github.com/aimhubio/aim). The backend is reimplemented (FastAPI, FoundationDB, Kafka, S3); the original Aim frontend (React UI) is preserved and served separately. Training clients log via the **frontier** (WebSocket + presigned S3); the UI and control operations talk to the **backend** REST API.

## Repo layout

| Path | Purpose |
|------|---------|
| **`extra/matyan-backend/`** | REST API, FDB storage, ingestion/control Kafka workers, CLI (reindex, backup, cleanup). [README](extra/matyan-backend/README.md) |
| **`extra/matyan-frontier/`** | Ingestion gateway: WebSocket + presigned S3 URLs; publishes to Kafka. [README](extra/matyan-frontier/README.md) |
| **`extra/matyan-ui/`** | React frontend (from Aim) + Python wrapper for serving. [README](extra/matyan-ui/README.md) |
| **`extra/matyan-client/`** | Python client SDK (Aim-compatible API); connects to frontier and backend. |
| **`extra/matyan-api-models/`** | Shared Pydantic models (WS, Kafka, REST). [README](extra/matyan-api-models/README.md) |
| **`extra/aim/`** | Original Aim codebase — reference only; not used at runtime. |
| **`deploy/helm/matyan/`** | Helm chart for Kubernetes (API, frontier, UI, workers, FDB, Kafka, S3). [README](deploy/helm/matyan/README.md) |
| **`scripts/`** | Seed data, smoke tests, and other one-off scripts. |
| **`docker-compose.yml`** | Local dev: FDB, Kafka, S3 (RustFS/MinIO), optional app services. |

## Architecture (summary)

- **Reads** (UI): UI → backend REST API → FoundationDB.
- **Ingestion** (training): Client → frontier (WebSocket / presigned S3) → Kafka → backend workers → FoundationDB (and S3 for blobs).
- **Control** (delete, rename, etc.): UI → backend REST API → FoundationDB + Kafka control-events → workers (e.g. S3 cleanup).

All app services are stateless and horizontally scalable. See [.cursor/rules/matyan-project-context.mdc](.cursor/rules/matyan-project-context.mdc) for full design and data flow.

## Quick start (local)

1. **Infrastructure only** (FDB, Kafka, S3):

   ```bash
   ./dev/compose-cluster.sh up -d
   ```

   Then run backend, frontier, and UI from the repo (see each package README for `uv run` commands).

2. **Full stack via Docker** (if services are defined in `docker-compose.yml`):

   ```bash
   ./dev/compose-cluster.sh up -d
   ```

3. **Kubernetes**: Use the Helm chart:

   ```bash
   helm install matyan deploy/helm/matyan -f deploy/helm/matyan/values-dev.yaml
   ```

   See [deploy/helm/matyan/README.md](deploy/helm/matyan/README.md) for values and production notes.

## Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) for backend, frontier, client, and API models.
- **Node.js** for building the UI (see [extra/matyan-ui/README.md](extra/matyan-ui/README.md)).
- **Docker / Docker Compose** for local FDB, Kafka, and S3.
- **kubectl + Helm** for Kubernetes deployment.

## Tooling

- Dependencies: `uv sync` (per package under `extra/`).
- Lint/format: `uvx ruff check .` and `uvx ruff format .`.
- Type check: `uvx ty check` (from repo root or per package).

## Component READMEs

- [Matyan Backend](extra/matyan-backend/README.md) — API, workers, config, deployment.
- [Matyan Frontier](extra/matyan-frontier/README.md) — Ingestion gateway, WebSocket, presigned URLs.
- [Matyan UI](extra/matyan-ui/README.md) — Frontend build, serve, and env.
- [Matyan API Models](extra/matyan-api-models/README.md) — Shared Pydantic models.
- [Helm Chart](deploy/helm/matyan/README.md) — Kubernetes deployment and configuration.
