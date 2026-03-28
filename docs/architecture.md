---
icon: material/domain
---

# Architecture

High-level design of Matyan: storage, ingestion, and serving.

## Components

| Service | Role |
|---------|------|
| **matyan-backend** | FastAPI REST API. Reads from FoundationDB; handles control operations (delete run, rename experiment, etc.) with synchronous FDB writes and Kafka events for async side effects. |
| **matyan-frontier** | Ingestion gateway. WebSocket for metrics/params; presigned URLs for large blobs (S3, GCS, Azure). Publishes to Kafka only. |
| **ingestion-workers** | Consume `data-ingestion` topic; write runs, sequences, and metadata to FoundationDB. |
| **control-workers** | Consume `control-events` topic; perform cloud storage cleanup (S3, GCS, Azure) and other side effects. |
| **matyan-client** | Python SDK. Sends tracking data to frontier; uses backend for metadata and queries. |
| **matyan-ui** | React UI; talks to matyan-backend. |

## Data flow

- **Reads:** UI or client → backend (REST) → FoundationDB.
- **Writes (training):** Client → frontier (WebSocket or presigned URLs) → Kafka → ingestion workers → FoundationDB (and S3/GCS/Azure for blobs).
- **Control:** UI → backend (REST) → FDB + Kafka control-events → control workers (e.g. storage cleanup).

## Storage (FoundationDB)

- **Key space:** Runs, sequences, and indexes live under FDB directories (e.g. `data/runs`, `data/indexes`, `system`). Keys use `fdb.tuple` encoding.
- **Indexes:** Tier 1 (archived, experiment, tag, created_at, etc.) and Tier 2 (scalar hyperparameters) are maintained on write and used by the query planner for MatyanQL.

The following section documents the concrete key layout for reference and debugging.

## FoundationDB key structure

The backend uses three top-level **directories** (FDB directory layer), each exposing a **subspace** for key-value storage. All keys are tuple-encoded with `fdb.tuple`; values are msgpack-serialized (see `storage/encoding.py`). Nested structures (e.g. run metadata, attributes) are stored as **trees**: each leaf is a key ending with a sentinel (e.g. `__leaf__`) so that `subspace.range(path)` returns all keys under that path.

### Top-level directories

| Directory path   | Subspace usage |
|-----------------|----------------|
| `("data", "runs")`    | Run data: metadata, attributes, traces, contexts, run–tag links, and all time-series sequences. |
| `("data", "indexes")` | Secondary indexes (Tier 1–3) and reverse index for deindexing; deletion tombstones. |
| `("system",)`         | Entities (experiments, tags, dashboards, reports, notes), run–experiment and run–tag mappings, project settings, ping key. |

### Data directory: `data/runs`

All keys are under a single **runs** subspace. `run_hash` is the run’s unique id (e.g. UUID or hash).

| Key tuple pattern | Description |
|-------------------|-------------|
| `(run_hash, "meta", <field>, "__leaf__")` | Run metadata: `name`, `description`, `created_at`, `updated_at`, `finalized_at`, `is_archived`, `active`, `experiment_id`, `client_start_ts`, `duration`, `pending_deletion`. Stored as a flat key per field (tree with leaf sentinel). |
| `(run_hash, "attrs", <path...>, "__leaf__")` or list/dict sentinels | Run attributes (e.g. hyperparameters under `hparams`). Nested dicts/lists flattened; scalars use `__leaf__`. Special key `attrs.__blobs__` holds blob references (S3/GCS/Azure keys). |
| `(run_hash, "traces", ctx_id, name, "dtype")` | Trace metadata: `dtype`, optional `last`, `last_step` per (context_id, metric_name). |
| `(run_hash, "contexts", ctx_id)` | Context dict for the given context id (deterministic id from context hash). |
| `(run_hash, "tags", tag_uuid)` | Run–tag association (value is truthy; used for “this run has this tag”). |
| `(run_hash, "seqs", ctx_id, name, col, step)` | Time-series columns: `col` is one of `"val"`, `"step"`, `"epoch"`, `"time"`. `step` is the step index. One key per (context, sequence name, column, step). |

So for a given run you have: **meta** (run-level fields), **attrs** (tree of attributes), **traces** (per-context per-metric metadata), **contexts** (context id → dict), **tags** (set of tag UUIDs), and **seqs** (time-series values and optional step/epoch/time columns).

### Data directory: `data/indexes`

Index entries live in the **indexes** subspace. Values are empty bytes; the payload is the run hash (and optionally other fields) in the key. Range scans on a prefix return matching run hashes. A **reverse index** under `_rev` allows O(1) removal of all index entries for a run when the run is deleted or updated.

**Tier 1 (structured fields):**

| Key tuple | Purpose |
|-----------|---------|
| `("archived", <bool>, run_hash)` | Filter by archived flag. |
| `("active", <bool>, run_hash)` | Filter by active (e.g. live runs). |
| `("experiment", <exp_name>, run_hash)` | Filter by experiment name. |
| `("created_at", <timestamp>, run_hash)` | Range scan by creation time. |
| `("tag", <tag_name>, run_hash)` | Filter by tag name. |

**Tier 2 (hyperparameters):**

| Key tuple | Purpose |
|-----------|---------|
| `("hparam", <param_name>, <value>, run_hash)` | Equality/range on top-level scalar hparams. |

**Tier 3 (metric trace names):**

| Key tuple | Purpose |
|-----------|---------|
| `("trace", <metric_name>, run_hash)` | Lookup runs that have a given metric. |

**Maintenance:**

| Key tuple | Purpose |
|-----------|---------|
| `("_rev", run_hash, <forward_key_elements>...)` | Reverse index: same elements as the forward key with `run_hash` prepended; used to delete all index entries for a run. |
| `("_deleted", run_hash)` | Tombstone: run was deleted; ingestion workers skip re-creating it. See [Understanding — Tombstones](understanding/tombstones.md). |

### System directory: `system`

**Entities** (experiments, tags, dashboards, dashboard apps, reports, notes) are stored as one key per field per entity; a “by name” index gives UUID from name where applicable.

| Key tuple pattern | Description |
|-------------------|-------------|
| `("experiments", uuid, field)` | Experiment record fields (e.g. name, description). |
| `("experiments_by_name", name)` | Name → experiment UUID. |
| `("experiment_runs", exp_uuid, run_hash)` | Experiment ↔ run association. |
| `("run_experiment", run_hash)` | Run → experiment UUID (reverse lookup). |
| `("tags", uuid, field)` | Tag record fields. |
| `("tags_by_name", name)` | Name → tag UUID. |
| `("run_tags", run_hash, tag_uuid)` | Run–tag link (also stored in runs_dir for co-location). |
| `("tag_runs", tag_uuid, run_hash)` | Tag → runs. |
| `("dashboards", uuid, field)` | Dashboard entity fields. |
| `("dashboard_apps", uuid, field)` | Dashboard app fields. |
| `("reports", uuid, field)` | Report fields. |
| `("notes", uuid, field)` | Note fields. |

**Project and UI state:**

| Key tuple pattern | Description |
|-------------------|-------------|
| `("project", key, "__leaf__")` | Project-level settings (e.g. name, description). |
| `("pinned_sequences", "__leaf__")` | Pinned sequence list for the UI. |
| `("__ping__",)` | Used by the backend for a minimal read to verify FDB connectivity. |

### Encoding and tree convention

- **Values:** msgpack via `storage/encoding.py` (with datetime extension).
- **Tree storage:** Nested dicts/lists are flattened into key paths. Scalars are stored with a final `__leaf__` component so that `subspace.range((run_hash, "meta"))` returns all meta keys. Empty dict/list use sentinels `__empty_dict__` / `__empty_list__`.

## Next

- [Getting started](getting-started.md) — Run the stack locally.
- [Advanced](advanced/index.md) — Per-component design and architectural decisions (backend, frontier, workers, FDB, Kafka, Cloud Storage, UI, client SDK).
