---
icon: material/api
---

# API

REST and streaming endpoints provided by **matyan-backend** for the UI and **matyan-client**.

## Base URL

Default: `http://localhost:53800`. All routes are under `/api/v1` (or as configured).

## Overview

- **Runs** — CRUD, archive, delete, tags, notes, logs (terminal + structured records), streaming search (run search, metric search, active runs, metric alignment).
- **Experiments** — CRUD, runs listing, notes, activity.
- **Tags** — CRUD, search, tagged runs.
- **Projects** — Info, activity, params aggregation, pinned sequences.
- **Dashboards / dashboard apps / reports** — Full CRUD.
- **Custom objects** — Images, texts, distributions, audios, figures: search, get-batch, get-step, blob-batch (S3-backed blobs via encrypted URIs).

Streaming endpoints use a binary wire protocol (path-value codec). Metric arrays are encoded as `EncodedNumpyArray` for chart rendering.

## Compatibility

Request/response shapes and query semantics (MatyanQL, record_range, index_range, etc.) are designed for the UI and client.

## Next

- [Getting started](getting-started.md) — Run the backend and try the API.
- [Architecture](architecture.md) — How the backend fits in the stack.
