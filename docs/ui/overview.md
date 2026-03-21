---
icon: material/view-dashboard
---

# Matyan UI overview

The Matyan UI is a React app that talks to the **Matyan backend**. You get explorers, run management, and search (MatyanQL).

## How to open the UI

Point your browser at the **UI** URL — default port is **8000** (e.g. `http://localhost:8000` when running with Docker Compose). The UI is served as a separate service from the backend; see [Getting started](../getting-started.md) for your setup.

## Main features

- **Explorers** — Query and compare runs by metrics, params, images, and other tracked data. Each explorer uses MatyanQL to filter runs or sequences, then lets you group and compare (e.g. by hyperparameters).
- **Run management** — Search runs, open a single run page to see params, metrics, images, distributions, logs, and artifacts. Tag, archive, or delete runs from the UI (these hit the backend API).
- **Search** — MatyanQL in the search bar: filter by `run.experiment`, `run.hparams.lr`, `metric.name`, etc. Matyan’s backend uses indexes where possible for speed.
- **Saved states** — Save explorer state (queries, grouping) to reproduce or share views.

## Pythonic search

Search in the UI uses MatyanQL; you can filter runs, metrics, and custom objects. See [Search and MatyanQL](../understanding/search-and-matyanql.md) for syntax and examples.

## No local mode

All data is on the server; you open the backend URL. The UI never reads a local directory.
