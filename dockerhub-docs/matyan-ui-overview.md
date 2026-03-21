# Matyan UI — Docker Hub Repository Overview

**Matyan web UI** serves the React experiment-tracking dashboard and static assets. It is the user-facing application for browsing runs, metrics, hyperparameters, and artifacts. Part of the [Matyan](https://github.com/4gt-104/matyan-core) stack (experiment-tracking fork of Aim).

## What this image does

- Runs the **Matyan UI server** (FastAPI + pre-built React app).
- Serves the single-page application and injects configuration (backend URL, base path) at runtime via a Jinja-rendered HTML template.
- The UI communicates **only with matyan-backend** (REST API). It does not talk to the frontier or Kafka.

## Requirements

- **matyan-backend** must be running and reachable. The UI sends all API requests to the backend (runs, experiments, metrics, streaming, etc.).

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MATYAN_UI_API_HOST_BASE` | `http://localhost:53800` | Backend base URL. Set this so the UI can reach matyan-backend. |
| `MATYAN_UI_BASE_PATH` | `""` | URL path prefix for the UI (e.g. `/matyan`). |
| `MATYAN_UI_API_BASE_PATH` | `/api/v1` | Path suffix for backend API. |
| `MATYAN_UI_API_AUTH_TOKEN` | `""` | Optional bearer token for UI → backend requests. |
| `MATYAN_UI_HOST` | `0.0.0.0` | Bind address. |
| `MATYAN_UI_PORT` | `8000` | Bind port (often mapped to 53802 in deployment). |

## Quick run

```bash
docker run -p 53802:8000 \
  -e MATYAN_UI_PORT=8000 \
  -e MATYAN_UI_API_HOST_BASE=http://host.docker.internal:53800 \
  matyan-ui:latest
```

Then open `http://localhost:53802` (or the port you map). For Docker Compose or Kubernetes, set `MATYAN_UI_API_HOST_BASE` to the backend service URL.

## Tags and versioning

- `latest` — latest build.
- Semantic tags (e.g. `0.2.0`) — match the Matyan release. Override at build time with `--build-arg IMAGE_VERSION=x.y.z`.

## Related images

- **matyan-backend** — REST API and storage; required for the UI to function.
- **matyan-frontier** — Optional; used by training clients for ingestion. The UI does not connect to the frontier.

## Documentation

- **Source**: [https://github.com/4gt-104/matyan-core](https://github.com/4gt-104/matyan-core)
- **Docs**: [https://4gt-104.github.io/matyan-core/](https://4gt-104.github.io/matyan-core/)
- **License**: Apache-2.0
