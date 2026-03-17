---
icon: material/folder
---

# Logging artifacts with Matyan

Link files (e.g. configs, checkpoints) to a run. Matyan stores artifact **metadata** in FoundationDB and the **blob data** in S3. The client uploads blobs via **presigned S3 URLs** obtained from the frontier.

## Artifacts API

1. **Log a file:**

```python
from matyan_client import Run

run = Run(experiment="demo")
run.log_artifact("config.yaml", name="run-config")
run.close()
```

2. **Log a directory:**

```python
run.log_artifacts("checkpoints/", name="ckpts")
```

The client requests a presigned URL from the frontier, uploads the file(s) to S3, and the frontier publishes blob references to Kafka. Ingestion workers persist metadata to FDB so the UI and API can list and serve artifacts.

## Storage backend

- **S3** (or S3-compatible, e.g. MinIO) is used for artifact blobs. Configure the frontier and backend with the same bucket/endpoint and credentials (e.g. `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or IAM). The frontier generates presigned PUT URLs; clients upload directly to S3.
- There is **no local file-system artifact backend** for the client: all artifacts go through the frontier → S3 → FDB metadata.

## Viewing artifacts

Artifact metadata (and links to blobs) appear on the run detail page in the Matyan UI. The backend serves blob data via the blob-batch endpoint (with encrypted URIs) when the UI requests artifact content.
