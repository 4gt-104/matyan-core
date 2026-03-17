---
icon: material/lightbulb
---

# Understanding Matyan

Matyan is built around a few core ideas:

- **Run isolation** — Each training run is a logical unit; data is associated with a run and sent to a central backend (no local repo).
- **Scalability** — The backend is stateless and reads from FoundationDB; ingestion goes through the frontier and Kafka so you can run many parallel experiments and many workers.
- **Flexibility** — The UI and MatyanQL let you filter, group, and compare runs and metrics.

Matyan is made of the backend, frontier, workers, client, and UI. See [Architecture](../architecture.md) for their roles and data flow. You run the backend, frontier, and workers as separate services (e.g. Docker Compose or Kubernetes). See [Getting started](../getting-started.md) to run them locally.
