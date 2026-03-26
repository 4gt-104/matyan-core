---
icon: material/file-document-multiple
---

# Blob Storage Overview

Large binary objects (images, audio, artifacts, and other blobs) are stored in an **S3-compatible** or **Google Cloud Storage (GCS)** object store. Matyan uses Blob Storage only for **blob content**; metadata (which run, which sequence, step index) lives in **FoundationDB**. The frontier issues **presigned URLs** so clients upload directly to the storage bucket; the backend fetches from the bucket when serving blob content to the UI.

## Role

- **Blob storage** — Actual bytes (PNG, WAV, serialized figures, etc.) are stored in a single bucket (e.g. `matyan-artifacts`) under keys that include run and sequence identity. No blob bytes go through Kafka or the frontier.
- **Metadata in FDB** — Run attrs and sequence metadata (including Blob identifiers) are written by **ingestion workers** to FDB after the client uploads and the frontier publishes a **blob_ref** to Kafka.
- **Serving** — When the UI (or API) requests blob content (e.g. image batch, audio), the **backend** reads the blob identifier from FDB, fetches the object from the storage backend, and streams it back, often using **encrypted blob URIs** so that the client does not see raw internal keys.

## Architectural decisions

### Why Cloud Storage (not FDB) for blobs

- **Size and cost** — FDB is optimized for smaller values and transactional reads/writes. Large blobs (megabytes) would blow up transaction size and storage cost. Dedicated blob storage (S3/GCS) is designed for large objects and is cheaper at scale.
- **Streaming** — Serving a large file is a simple GET; the backend streams from the bucket to the client without loading the whole object into memory. FDB would require reading the value into memory or chunking.
- **Ecosystem** — S3, Google Cloud Storage, or MinIO are standard choices for ML artifacts and are often already present in data platforms. Matyan reuses them instead of inventing a custom blob store.

### Presigned URLs (client → Blob Storage directly)

Clients do **not** upload blob bytes to the frontier. Instead:

1. Client asks the frontier for a **presigned PUT URL** (e.g. `POST /api/v1/rest/artifacts/presign` with run id, sequence, step, etc.).
2. Frontier generates an internal object identifier, creates a presigned URL with a time-limited expiry, and publishes a **blob_ref** message to Kafka (so workers can write the key into FDB).
3. Client uploads the blob **directly to the Bucket** using the presigned URL.
4. Ingestion worker consumes the blob_ref and writes the object key (and any metadata) into FDB.

This avoids the frontier (or backend) being a bottleneck or proxy for large uploads and keeps the frontier stateless and lightweight.

### Single bucket, key layout

All blobs live in one configurable bucket. Key structure (e.g. run hash, sequence type, step) is chosen so that:

- **Listing by run** — Control worker (or cleanup jobs) can delete all objects under a run prefix when a run is deleted.
- **Uniqueness** — Key includes enough context (run, sequence, step, maybe index) so that concurrent uploads do not collide.

The exact key format is an implementation detail; the important point is that “all blobs for run X” can be enumerated and deleted by prefix.

### Backend fetches on read

When the UI requests blob content (e.g. for the image explorer), the backend looks up the identifier from FDB, fetches the object from Blob Storage using the same credentials/config as the workers, and streams it back. Cloud credentials are required by both the **frontier** (to generate presigned URLs), the **backend** (to serve blobs), and the **control worker** (to delete blobs). The frontier does not need to read from the bucket; it only generates URLs.

Responses that reference blobs (e.g. custom object search results) may expose an **encrypted blob URI** (Fernet) instead of the raw storage key. The UI or client sends this token to a backend endpoint (e.g. blob-batch), which decrypts it, fetches from Cloud Storage, and returns the bytes. This hides internal keys and bucket details from the client and allows the backend to enforce access control and audit.

### Control worker: Cleanup on run_deleted

When a run is deleted, the backend writes the deletion to FDB and publishes **run_deleted** to the control-events topic. The **control worker** consumes it and deletes all bucket objects under that run’s prefix. So blob lifecycle is tied to run lifecycle; if the control worker is down or the event is lost, blobs can be orphaned. A **periodic job** (e.g. cleanup-orphan-blobs CronJob) can scan FDB for deletion tombstones and remove leftover cloud objects to avoid unbounded storage growth.

## Related

- [Frontier](frontier.md) — Issues presigned URLs and publishes blob_ref.
- [Backend](backend.md) — Fetches blobs from Cloud Storage for API responses.
- [Workers](workers.md) — Control worker performs blob cleanup; ingestion worker writes blob refs to FDB.
- [FoundationDB](foundationdb.md) — Blob metadata and keys stored in FDB.
