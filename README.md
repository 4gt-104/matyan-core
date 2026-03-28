<div align="center">
  <img src="https://raw.githubusercontent.com/4gt-104/matyan-core/main/docs/static/logo.svg" width="200" alt="Matyan" />
  <h3>A scalable, self-hosted ML experiment tracker</h3>
  <p>Aim-compatible UI and SDK · FoundationDB · Kafka · Cloud Storage (S3, GCS, Azure)</p>
</div>

<br/>

<div align="center">

  [![PyPI - matyan-client](https://img.shields.io/pypi/v/matyan-client?color=teal&label=matyan-client)](https://pypi.org/project/matyan-client/)
  [![PyPI - matyan-backend](https://img.shields.io/pypi/v/matyan-backend?color=teal&label=matyan-backend)](https://pypi.org/project/matyan-backend/)
  [![PyPI - matyan-frontier](https://img.shields.io/pypi/v/matyan-frontier?color=teal&label=matyan-frontier)](https://pypi.org/project/matyan-frontier/)
  [![PyPI - matyan-ui](https://img.shields.io/pypi/v/matyan-ui?color=teal&label=matyan-ui)](https://pypi.org/project/matyan-ui/)
  [![PyPI - matyan-api-models](https://img.shields.io/pypi/v/matyan-api-models?color=teal&label=matyan-api-models)](https://pypi.org/project/matyan-api-models/)
  [![Python](https://img.shields.io/badge/python-%3E%3D%203.10-blue)](https://pypi.org/project/matyan-client/)
  [![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-blue)]()
  [![Docs](https://img.shields.io/badge/docs-stable-green)](https://4gt-104.github.io/matyan-core/stable/)

</div>

<br/>

<div align="center">
  <h4>
    <a href="#ℹ️-about"><b>About</b></a> &bull;
    <a href="#-quick-start"><b>Quick Start</b></a> &bull;
    <a href="#-architecture"><b>Architecture</b></a> &bull;
    <a href="#-repo-layout"><b>Repo</b></a> &bull;
    <a href="#-deployment"><b>Deployment</b></a> &bull;
    <a href="https://4gt-104.github.io/matyan-core/stable/"><b>Docs</b></a>
  </h4>
</div>

---

# ℹ️ About

Matyan (մատյան, *book of records* in Armenian) is a self-hosted ML experiment tracking stack forked from [Aim](https://github.com/aimhubio/aim). The backend is fully reimplemented on **FoundationDB**, **Kafka**, and **Cloud Storage** (S3, GCS, Azure) for horizontal scalability — while the original Aim React UI and Python client SDK API are preserved unchanged.

Matyan logs your training runs and any ML metadata, enables a beautiful UI to compare and observe them, and provides an SDK to query them programmatically.

<div align="center">
  <table>
    <tbody>
      <tr>
        <th>Log Metadata Across Your ML Pipeline 💾</th>
        <th>Visualize & Compare Metadata via UI 📊</th>
      </tr>
      <tr>
        <td>
          <ul>
            <li>Metrics, hyperparameters, images, audio, text, distributions</li>
            <li>Structured and terminal run logs</li>
            <li>Aim-compatible SDK — no code changes needed</li>
          </ul>
        </td>
        <td>
          <ul>
            <li>Metadata visualization via explorers (metrics, images, audio, …)</li>
            <li>Grouping, aggregation, and subplots</li>
            <li>Querying using MatyanQL (Python expressions)</li>
          </ul>
        </td>
      </tr>
      <tr>
        <th>Scale to Thousands of Runs ⚡</th>
        <th>Production-Ready Deployment 🚀</th>
      </tr>
      <tr>
        <td>
          <ul>
            <li>FoundationDB backend — handles 10,000s of runs</li>
            <li>Kafka-based ingestion pipeline with consumer workers</li>
            <li>Secondary indexes (Tier 1 + Tier 2 hparam) for fast queries</li>
          </ul>
        </td>
        <td>
          <ul>
            <li>Helm chart for Kubernetes with all components</li>
            <li>Stateless, horizontally scalable services</li>
            <li>S3, GCS, or Azure Blob Storage for large artifact blobs</li>
          </ul>
        </td>
      </tr>
    </tbody>
  </table>
</div>

<div align="center">
  <kbd>
    <img src="https://raw.githubusercontent.com/4gt-104/matyan-core/main/docs/static/demo.gif" alt="Matyan demo" />
  </kbd>
</div>

<br/>

<div align="center">
  <sub><strong>SEAMLESSLY INTEGRATES WITH:</strong></sub>
  <br/>
  <br/>
  <img src="https://user-images.githubusercontent.com/97726819/225954732-2b263308-8ed8-4df3-810b-704840328e98.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954727-04eccf0e-51ed-4f2d-8f3b-c9a675ca8e8f.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954728-ca2f498d-51a7-487b-bd69-ffb5f0c2af58.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954689-1076998c-42f4-4e31-ab47-d9f39575fda1.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954739-0231d659-3202-4458-9c35-ba92d1f079b8.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954697-ef2c7091-b089-4b68-8543-80ce7275b683.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954743-dbfe1e98-7b9f-446a-9fe4-ad4fd562f3df.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954736-7c52ab5a-6780-4375-a6f8-b394dae3ad31.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954707-4bc078b5-ae6f-4847-bc2c-3f81959accb2.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954725-a4d4c32c-75db-470a-b1da-698982faa23c.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954665-8d844747-a857-41b8-9104-7c27a8bdb81a.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954686-b9c8ec57-d4fc-44e1-a4b8-443db381a00f.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954674-42fbfdb3-0351-492d-9ea3-1d3ab2b545f5.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954678-25f1b626-2cb1-4e7e-ad83-f7c8ab679c6f.png" height="60" />
  <img src="https://user-images.githubusercontent.com/97726819/225954702-d18d2706-dc87-4e09-a678-f010f6d95736.png" height="60" />
</div>

---

# 🏁 Quick Start

## 1. Start the infrastructure

```bash
./dev/compose-cluster.sh up -d
```

This starts FoundationDB, Kafka, and S3 (RustFS) locally via Docker Compose. (GCS and Azure backends are supported in production).
Then start the backend, frontier, and UI from their package directories (see each component README for `uv run` commands).

## 2. Install the client

```bash
python3 -m pip install matyan-client
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add matyan-client
```

## 3. Log a training run

```python
from matyan_client import Run

run = Run()

run["hparams"] = {
    "learning_rate": 0.001,
    "batch_size": 32,
}

for i in range(100):
    run.track(i * 0.01, name="loss", step=i, context={"subset": "train"})
    run.track(1 - i * 0.01, name="acc", step=i, context={"subset": "train"})

run.close()
```

The same `Run` API works as in Aim — see [Supported types](https://4gt-104.github.io/matyan-core/stable/quick-start/supported-types/) for images, audio, distributions, figures, and text.

<details>
<summary><strong>Query runs programmatically via SDK</strong></summary>

</br>

```python
from matyan_client import Repo

repo = Repo("http://localhost:53800")

query = "metric.name == 'loss'"

for run_metrics_collection in repo.query_metrics(query).iter_runs():
    for metric in run_metrics_collection:
        params = metric.run[...]
        steps, values = metric.values.sparse_numpy()
```

</details>

<details>
<summary><strong>Deploy on Kubernetes</strong></summary>

</br>

```bash
helm install matyan deploy/helm/matyan -f deploy/helm/matyan/values-production.yaml
```

See [deploy/helm/matyan/README.md](deploy/helm/matyan/README.md) for all values and production notes.

</details>

Read the full documentation at [matyan-core/deployment](https://4gt-104.github.io/matyan-core/stable/deployment/production/) 📖

---

# 🏗 Architecture

```mermaid
flowchart TB
    subgraph clients["Training Clients"]
        C["matyan-client"]
    end

    subgraph ui["UI"]
        U["matyan-ui"]
    end

    subgraph ingestion["Ingestion path"]
        STR["Cloud Storage<br/>(S3 / GCS / Azure)"]
        K["Kafka<br/>data-ingestion"]
        IW["Ingestion Workers"]
    end

    subgraph control["Control path"]
        B["matyan-backend<br/>(REST API)"]
        KC["Kafka<br/>control-events"]
        CW["Control Workers"]
    end

    subgraph storage["Storage"]
        FDB["FoundationDB"]
    end

    C -->|"WebSocket (metrics, hparams)"| F
    C --| "PUT blob" | STR
    F --| "blob ref" | K
    IW --> STR
    CW --| "cleanup" | STR
```

| Concern | Entry point | Consistency |
|---|---|---|
| UI reads | matyan-backend | Immediate |
| UI control ops (delete, rename) | matyan-backend | Immediate for user, async for cleanup |
| Client metrics / hparams ingestion | frontier (WebSocket) | Eventual |
| Client blob upload (images, audio) | frontier (presigned URL) | Eventual |

---

# 📁 Repo Layout

| Path | Purpose |
|---|---|
| **`extra/matyan-backend/`** | REST API, FDB storage, ingestion/control Kafka workers, CLI. [README](extra/matyan-backend/README.md) |
| **`extra/matyan-frontier/`** | Ingestion gateway: WebSocket + presigned URLs (S3, GCS, Azure SAS); publishes to Kafka. [README](extra/matyan-frontier/README.md) |
| **`extra/matyan-ui/`** | React frontend (from Aim) + Python wrapper for serving. [README](extra/matyan-ui/README.md) |
| **`extra/matyan-client/`** | Python client SDK (Aim-compatible API); connects to frontier and backend. |
| **`extra/matyan-api-models/`** | Shared Pydantic models (WS, Kafka, REST). [README](extra/matyan-api-models/README.md) |
| **`deploy/helm/matyan/`** | Helm chart for Kubernetes. [README](deploy/helm/matyan/README.md) |
| **`dev/docker-compose.yml`** | Local dev: FDB, Kafka, S3 (RustFS), optional app services. |
| **`docs/`** | MkDocs source for the documentation site. |

---

# 🚢 Deployment

## Local development

The fastest way to get everything running is Docker Compose. A single script starts all infrastructure dependencies and the Matyan services:

```bash
./dev/compose-cluster.sh up -d
```

This brings up:

| Service | Port | Purpose |
|---|---|---|
| FoundationDB | — | Primary storage (internal) |
| Apache Kafka | 9092 | Ingestion + control event bus |
| RustFS (S3-compatible) | 9000 / 9001 | Blob artifact storage + console |
| `matyan-backend` | 53800 | REST API |
| `matyan-frontier` | 53801 | WebSocket ingestion gateway |
| `matyan-ui` | 8000 | React UI |

Point your browser to `http://localhost:8000` once all services are healthy. Use `http://localhost:9001` for the RustFS console (credentials: `rustfsadmin` / `rustfsadmin`).

To seed demo data into a running stack:

```bash
cd extra/matyan-backend
uv run python scripts/seed_data.py seed
```

## Kubernetes

Matyan ships a Helm chart covering all application services and their infrastructure dependencies (FoundationDB via the `fdb-operator`, Kafka, RustFS).

**Prerequisites**: a Kubernetes cluster (1.25+) with a default or named `StorageClass`.

**Generate a Fernet key** (required for encrypted blob URIs):

```bash
uvx --from cryptography python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Install the chart:**

```bash
helm install matyan deploy/helm/matyan \
  -f deploy/helm/matyan/values-dev.yaml \
  --set ui.hostBase=https://matyan.example.com \
  --set backend.hostBase=https://matyan.example.com \
  --set blobUriSecret.value=<your-fernet-key> \
  --set fdb-cluster.processes.general.volumeClaimTemplate.storageClassName=<your-storage-class>
```

**Scaling**: all application services (`matyan-backend`, `matyan-frontier`, ingestion workers, control workers) are stateless. Scale any of them independently by adjusting `replicaCount` in the values file — FoundationDB and Kafka handle coordination automatically.

See [deploy/helm/matyan/README.md](deploy/helm/matyan/README.md) for the full values reference and production configuration notes (TLS, resource limits, external Kafka/S3, multi-node FDB).

---

# 🆚 Comparisons to familiar tools

<details>
<summary>
  <strong>TensorBoard vs Matyan</strong>
</summary>

</br>

**Training run comparison**

- Tracked parameters are first-class citizens in Matyan. You can search, group, and aggregate by params — deeply exploring all tracked data (metrics, hyperparameters, images, audio) in the UI.
- With TensorBoard, users are forced to encode parameters into the run name to search and compare them. **TensorBoard has no grouping, aggregation, or subplot features.**

**Scalability**

- Matyan is built on FoundationDB and Kafka to handle 10,000s of training runs at both the storage and UI layers.
- TensorBoard becomes slow and hard to use when a few hundred training runs are queried or compared.

</details>

<details>
<summary>
  <strong>MLflow vs Matyan</strong>
</summary>

</br>

MLflow is an end-to-end ML lifecycle tool. Matyan is focused on training tracking and observability.

**Run comparison**

- Matyan treats tracked parameters as first-class citizens. Users can query runs, metrics, images, and filter using params with full grouping, aggregation, and subplotting.
- MLflow has basic search by config but lacks grouping, aggregation, and rich comparison features.

**UI scalability**

- Matyan's UI handles thousands of metrics with thousands of steps smoothly.
- MLflow's UI slows noticeably with a few hundred runs.

**Deployment**

- Both are self-hosted and open-source.
- Matyan adds a Kafka-based ingestion pipeline and FoundationDB for high-throughput, horizontally scalable deployments.

</details>

<details>
<summary>
  <strong>Weights and Biases vs Matyan</strong>
</summary>

</br>

**Hosted vs self-hosted**

- Weights and Biases is a hosted, closed-source MLOps platform. Your experiment data lives on their servers.
- Matyan is fully self-hosted and open-source — your data stays in your own infrastructure (FoundationDB + S3/GCS/Azure).

**Cost**

- W&B charges per seat / usage at scale.
- Matyan is free; you only pay for your own compute and storage.

</details>

<details>
<summary>
  <strong>Aim vs Matyan</strong>
</summary>

</br>

Matyan is a fork of Aim. The UI and Python SDK API surface are almost **identical** — minor code changes needed to switch.

**Storage backend**

- Aim uses an embedded RocksDB store (custom Cython extensions) on a single node. Storage is tied to the machine running `aim up`.
- Matyan replaces RocksDB with **FoundationDB** — a distributed, ACID-compliant key-value store designed for horizontal scaling. All runs share a single logical key space across a cluster.

**Ingestion pipeline**

- Aim writes tracking data synchronously in the same process as the server.
- Matyan routes tracking data through **Kafka** → ingestion workers → FoundationDB, decoupling the write path from the API. The frontier service can handle bursts from many concurrent training jobs without backpressure on the API.

**Deployment model**

- Aim is a single `aim up` process — simple to start, harder to scale.
- Matyan is a set of stateless, horizontally scalable microservices (backend API, frontier, ingestion workers, control workers) deployable on Kubernetes via Helm.

**When to use Aim**

Aim is a great choice for individual researchers running experiments on a single machine where simplicity matters more than scale.

**When to use Matyan**

Matyan is the right choice when you need to scale to many concurrent training jobs, many users, or large run counts — while keeping the familiar Aim UI and SDK.

</details>

---

# 📦 Component READMEs

- [Matyan Backend](https://github.com/4gt-104/matyan-backend) — REST API, FDB storage, workers, config, deployment.
- [Matyan Frontier](https://github.com/4gt-104/matyan-frontier) — Ingestion gateway, WebSocket, presigned URLs (S3/GCS/Azure).
- [Matyan UI](https://github.com/4gt-104/matyan-ui) — Frontend build, serve, and environment variables.
- [Matyan API Models](https://github.com/4gt-104/matyan-api-models) — Shared Pydantic models.
- [Helm Chart](deploy/helm/matyan/README.md) — Kubernetes deployment and configuration.

---

# 📬 Contact

Questions, feedback, or collaboration? Reach out at [grigoryan.tigran119@gmail.com](mailto:grigoryan.tigran119@gmail.com).

---

# ⚖️ License

Apache 2.0 — see [LICENSE](LICENSE).

Matyan is a fork of [Aim](https://github.com/aimhubio/aim) by AimStack, used under the Apache 2.0 license.
