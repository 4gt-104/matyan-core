---
icon: material/cloud
---

# Cloud Storage Configuration

Matyan officially supports three robust cloud blob storage backends for persisting heavy artifacts, sequences, images, and audio seamlessly: **Amazon Web Services S3**, **Google Cloud Storage (GCS)**, and **Microsoft Azure Blob Storage**.

Blob storage allows the ingestion frontier to remain incredibly lightweight and highly available, acting as an authentication proxy to generate presigned upload URLs for remote clients, while metadata coordinates asynchronously via FoundationDB and Kafka.

## Amazon S3 (Default)

AWS S3 is the default storage backend for Matyan deployments.

### Configuration
To deploy Matyan using an S3-compatible backend, provide the following environment variables to the backend and frontier configurations:

```env
BLOB_BACKEND_TYPE=s3
S3_BUCKET=matyan-artifacts
S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

### Authentication
Authentication is facilitated by direct `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` key pairs. Support is inherently baked through Python's `boto3` and `aioboto3` libraries.

---

## Google Cloud Storage (GCS)

You can natively configure Matyan to interact with Google Cloud environments using `google-cloud-storage` drivers directly without enforcing S3-interoperability overrides.

### Configuration
Toggle the backend protocol to `gcs` and specify the deployment bucket. You do not manually supply connection URLs.

```env
BLOB_BACKEND_TYPE=gcs
GCS_BUCKET=matyan-artifacts-gcs
```

### Authentication
Matyan enforces standard Google Cloud security practices. It autonomously determines correct environment credentials via Google's `GOOGLE_APPLICATION_CREDENTIALS` resolution strategy. Provide a valid Service Account JSON mapping to the container environments:

```env
GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json
```

**Note:** The service account must possess `Storage Object Admin` or equivalent permissions since generating Signed URLs requires an RSA Private Key. Anonymous default credentials will throw exceptions if utilized within the frontier endpoint generator.

## Azure Blob Storage (Azure)

Azure Blob Storage provides container‑based object storage. Matyan can generate SAS tokens for presigned uploads and use the Azure SDK for cleanup.

### Configuration
Provide the following environment variables to both the backend and frontier:

```env
BLOB_BACKEND_TYPE=azure
AZURE_CONTAINER=matyan-artifacts
# Either a connection string or an account URL with appropriate credentials
AZURE_CONN_STR=DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net
# Optional: use account URL if you prefer SAS token generation via user delegation
# AZURE_ACCOUNT_URL=https://youraccount.blob.core.windows.net
```

### Authentication
Azure authentication can be performed via a full connection string (`AZURE_CONN_STR`) or via an account URL (`AZURE_ACCOUNT_URL`) combined with a SAS token or managed identity. The frontier generates SAS URLs for direct client uploads, and the control worker uses the Azure SDK to delete blobs on run deletion.
