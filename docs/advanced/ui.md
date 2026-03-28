---
icon: material/monitor-dashboard
---

# UI (matyan-ui)

The **matyan-ui** is the web frontend for browsing runs, metrics, custom objects, logs, and experiments. It is a **React** single-page application (SPA) served by a thin Python wrapper. It communicates **only** with the **matyan-backend** REST API; it never talks to the frontier, Kafka, or FDB.

## Role

- **Run management** — List runs, filter by experiment/tag/MatyanQL, open run detail, delete/archive runs, add/remove tags.
- **Metrics and charts** — Query metrics, align series, render charts (using the same streaming and encoding contract as the original Aim UI).
- **Custom objects** — Images, audio, text, distributions, figures: search, batch fetch, step-level view. Blob content is fetched via the backend (which reads from S3/GCS/Azure).
- **Logs** — Terminal log lines and structured log records, with range and level filters.
- **Experiments, tags, dashboards** — CRUD and association to runs.

All of this is done by calling the backend’s REST and **binary streaming** endpoints. The UI is a client of the backend only.

## Architectural decisions

### Backend-only (no frontier, no WebSocket to UI)

The UI does **not** connect to the frontier or any WebSocket for real-time ingestion. Reasons:

- **Simpler deployment** — One API base URL (backend). No need to expose the frontier to the browser or to manage a second WebSocket endpoint for the UI.
- **Security and topology** — The frontier is for **training clients** (ingestion). The UI is for **humans** (read and control). Keeping them separate lets you put the backend (and UI) behind one ingress and keep the frontier on a different network or port if desired.
- **Consistency** — All data the UI shows comes from the backend, which reads from FDB (and S3/GCS/Azure for blobs). So the UI always sees a consistent view of “what’s stored,” regardless of ingestion lag. Live training progress is reflected only after ingestion workers have written to FDB; the UI does not need a live stream of every metric point.

### Polling for updates (no WebSocket to backend)

The UI does **not** hold a WebSocket to the backend for “live” updates. It uses **periodic polling** (e.g. re-fetch run list or run detail on an interval) when the user is on a page that shows run status or metrics. So:

- Backend stays **stateless** (no long-lived connections per user).
- No sticky sessions or connection state to manage across replicas.
- Polling interval can be tuned (e.g. faster when “active runs” exist, slower when idle). Optional optimizations (e.g. “changed since” endpoint, ETag) can reduce payload size without adding WebSocket complexity.

### Same UI codebase as Aim (compatibility)

The React app is derived from the original Aim UI so that the look, features, and UX stay familiar. The **protocol** (REST paths, query params, binary streaming format) is reimplemented on the backend to be compatible. So the same UI bundle works against the Matyan backend without rewriting the frontend; only the backend URL and env (e.g. API host base) need to be configured.

### Served by a Python wrapper

The UI is built as a static SPA (HTML/JS/CSS). In production it is served by a small **Python** server (matyan-ui package) that:

- Serves the static assets and index.html.
- Injects or reads **configuration** (e.g. backend API base URL, base path) so the SPA knows where to send requests.
- Can run in the same pod as the “UI” deployment in Kubernetes; the ingress routes `/` to this service and `/api/` to the backend (and frontier paths as configured).

So “UI” in deployment terms is this wrapper process, not a separate Node server; the React app is pre-built and static.

### No server-side session or auth in the chart

The default Helm chart does not implement authentication. The UI and backend are configured with hostnames and (optionally) a static API token for UI → backend calls. Auth (e.g. OAuth, SSO) can be added at the ingress or backend layer without changing the UI’s contract (same REST API, with auth headers or cookies as required).

## Related

- [Backend](backend.md) — The only service the UI talks to.
- [Architecture](../architecture.md) — High-level data flow (UI → backend → FDB/S3/GCS/Azure).
- [Matyan UI overview](../ui/overview.md) — User-facing UI features and access.
