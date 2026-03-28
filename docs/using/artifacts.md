---
icon: material/folder
---

# Logging artifacts with Matyan

Link files (e.g. configs, checkpoints) to a run. Matyan stores artifact **metadata** in FoundationDB and the **blob data** in an external object store. The client uploads blobs via **presigned URLs** obtained from the frontier.

Three storage backends are supported: **AWS S3** (or S3-compatible), **Google Cloud Storage (GCS)**, and **Azure Blob Storage**.

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

The client requests a presigned URL from the frontier, uploads the file(s) to the configured storage backend, and the frontier publishes blob references to Kafka. Ingestion workers persist metadata to FDB so the UI and API can list and serve artifacts.

## Storage backends

Configure the storage backend by setting `BLOB_BACKEND_TYPE` to `s3` (default), `gcs`, or `azure` on both the frontier and backend services.

### AWS S3 (and S3-compatible)
- **Backend Type:** `s3`
- **Upload Flow:** The frontier generates a standard S3 presigned `PUT` URL. The client performs a `PUT` request with the binary data.
- **Configuration:**
    - `S3_ENDPOINT`: API endpoint (e.g., `https://s3.amazonaws.com` or `http://localhost:9000` for RustFS).
    - `S3_PUBLIC_ENDPOINT`: Optional public URL for clients if different from internal endpoint.
    - `S3_ACCESS_KEY` / `S3_SECRET_KEY`: Credentials.
    - `S3_BUCKET`: Target bucket name.
    - `S3_REGION`: AWS region (default: `us-east-1`).

### Google Cloud Storage (GCS)
- **Backend Type:** `gcs`
- **Upload Flow:** The frontier generates a V4 signed `PUT` URL. The client performs a `PUT` request with the binary data.
- **Configuration:**
    - `GCS_BUCKET`: Target bucket name.
    - **Authentication:** Handled via Google Application Default Credentials (ADC). Ensure the service account has `roles/storage.objectCreator` and `roles/storage.objectViewer` permissions.

### Azure Blob Storage
- **Backend Type:** `azure`
- **Upload Flow:** The frontier generates a Shared Access Signature (SAS) token with `write` permission. The client performs a `PUT` request to the SAS-authenticated URL.
- **Crucial Note:** Azure requires the `x-ms-blob-type: BlockBlob` header for blob uploads. The frontier returns this header in the `headers` field of the presign response, and the `matyan-client` applies it automatically.
- **Configuration:**
    - `AZURE_CONTAINER`: Target container name.
    - `AZURE_CONN_STR`: Connection string (primary authentication method).
    - `AZURE_ACCOUNT_URL`: Account URL (e.g., `https://<account>.blob.core.windows.net`) used with `DefaultAzureCredential`.

## Viewing artifacts

Artifact metadata (and links to blobs) appear on the run detail page in the Matyan UI. The backend serves blob data via the blob-batch endpoint (with encrypted URIs) when the UI requests artifact content. The backend decrypts the URI, fetches the data from the configured storage backend, and streams it back to the browser.

