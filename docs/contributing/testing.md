---
icon: material/test-tube
---

# Testing

## Unit tests

Unit tests live inside each package (`extra/matyan-backend/tests/`, `extra/matyan-client/tests/`, `extra/matyan-frontier/tests/`). They use mocks for external services (Kafka, S3, HTTP) and run against a real FoundationDB when required. Run them from each package:

- `cd extra/matyan-backend && uv run pytest`
- `cd extra/matyan-client && uv run pytest`
- `cd extra/matyan-frontier && uv run pytest`

No Docker or external services are required for unit tests (except FDB for backend storage/API tests if not mocked).

## Integration tests

Integration tests run against **real** services: backend, frontier, Kafka, FDB, and (for some tests) ingestion and control workers. They live in **`tests/integration/`** at the repository root and are **additive** — no existing unit tests are removed or modified.

### Prerequisites

1. Start services (e.g. with Docker Compose):

   ```bash
   ./dev/compose-cluster.sh up -d
   ```

2. Wait until the backend and frontier are healthy (e.g. `GET http://localhost:53800/health/ready/` and `GET http://localhost:53801/health/ready/` return 200).

### Running integration tests

From the **matyan-core** directory, with the **integration** dependency group (so that `matyan-client`, `matyan-backend` and `matyan-frontier` are available):

```bash
./dev/install_all_components.sh
python3 -m pytest tests/integration -v
```

To run only tests marked as integration (when using the same command from a directory that collects more tests):

```bash
python3 -m tests/integration -m integration -v
```

### Behavior when services are down

If the backend, frontier, or Kafka are not reachable, integration tests **skip** instead of failing. So you can run the same test tree in CI (with `./dev/compose-cluster.sh up -d`) or locally without compose; tests that need a service will skip when it is unavailable.

### What is covered

| Test file | Covers |
|-----------|--------|
| `test_backend_kafka.py` | Backend control events (e.g. delete run) published to Kafka |
| `test_client_backend.py` | HttpTransport, Repo, backup, restore against live backend |
| `test_frontier_kafka.py` | Frontier WebSocket and presign; messages on Kafka |
| `test_client_frontier.py` | Run over real WS/HTTP; run appears in backend after close |
| `test_full_pipeline.py` | Full pipeline: client → frontier → Kafka → worker → FDB → read |
| `test_worker_ingestion.py` | Kafka → ingestion worker → FDB; verify via backend API |
| `test_worker_control.py` | Delete run with blob ref → `run_deleted` on control-events |
