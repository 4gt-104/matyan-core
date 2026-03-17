---
icon: material/scale-balance
---

# Public API and versioning

This page describes what Matyan considers **public API**, how packages are versioned, and how the **matyan-core** repository is tagged.

## What is public API?

Only the following are considered **public API** and are covered by stability guarantees:

| Surface | What is public |
|--------|-----------------|
| **matyan-client** | The **`Run`** and **`Repo`** classes and their documented methods and attributes; and the custom object types **`Distribution`**, **`Image`**, **`Audio`**, **`Text`**, and **`Figure`** (used with `run.track()` for logging distributions, images, audio, text, and figures). This is the SDK surface that training scripts and tools use. |
| **matyan-backend** | The **REST API** exposed under `/api/v1` (routes, request/response shapes, query semantics such as MatyanQL, record_range, etc.). This is what the UI and client use to read and control data. |

Everything else is **private API**:

- **matyan-frontier** — ingestion gateway (WebSocket protocol, internal message shapes).
- **matyan-api-models** — shared Pydantic models between frontier, backend, and workers; not a user-facing package.
- **matyan-backend** internals — storage layer, workers, Kafka integration, internal modules.
- **matyan-client** internals — transport, cache, blob uploader, and any module or symbol not part of the documented `Run`, `Repo`, or custom object types (`Distribution`, `Image`, `Audio`, `Text`, `Figure`) API.
- **matyan-ui** — frontend implementation details.

Do not rely on private APIs; they may change in any release without notice.

## Package versioning

Matyan is split into **multiple Python packages**, each with its own version (e.g. in `pyproject.toml`). All of them follow **semantic versioning** (major.minor.patch).

As a **user**, you only need to care about the versions of:

- **matyan-client** — when you install or upgrade the client SDK.
- **matyan-backend** — when you deploy or upgrade the server (REST API).

The other packages (matyan-frontier, matyan-api-models, matyan-ui, etc.) are not part of the public API. Their versions are relevant only for internal development and integration within the monorepo; you do not need to track them for compatibility.

## matyan-core tags and releases

**matyan-core** is the main repository that accumulates all Matyan projects (backend, frontier, client, UI, workers, etc.). It is the primary reference for users.

Releases and **git tags** of matyan-core are based on **public API changes** only:

- A **major** tag (e.g. `v2.0.0`) is used when the public API has breaking changes (e.g. breaking changes in `Run`, `Repo`, the custom object types, or the backend REST API).
- **Minor** and **patch** tags reflect backward-compatible public API changes or fixes.

If an internal component (e.g. **matyan-frontier**) introduces a breaking change and bumps its own major version, that does **not** necessarily result in a new major release of matyan-core. As long as the public API (matyan-client `Run`, `Repo`, custom object types, and backend REST API) is unchanged, matyan-core may only be tagged with a **patch** or **fix** release (e.g. `v1.2.3` → `v1.2.4`). Conversely, any breaking change to the public API will be reflected in matyan-core’s version (e.g. a new major version).

When choosing a version of Matyan to use or when reading the changelog, focus on **matyan-core** tags and on **matyan-client** / **matyan-backend** versions; that is where public API stability is expressed.
