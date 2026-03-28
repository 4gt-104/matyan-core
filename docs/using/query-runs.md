---
icon: material/database-search
---

# Query runs and objects

Use the `Repo` object (see [Concepts](../understanding/concepts.md)) to query runs and their data. `Repo` points at the **Matyan backend** URL; all queries go over the REST API.

## Initialize Repo

```python
from matyan_client import Repo

repo = Repo("http://localhost:53800")
```

## Iterate over runs

```python
for run in repo.iter_runs():
    print(run.hash, run["hparams"])
```

## Query metrics with MatyanQL

Use the same MatyanQL expressions as in the UI (see [Search (MatyanQL)](search.md)). Query results are streamed from the backend.

```python
query = "run.hparams.lr == 0.001"

for run_metrics in repo.query_metrics(query).iter_runs():
    for metric in run_metrics:
        params = metric.run[...]           # run params
        steps, values = metric.values.sparse_numpy()  # metric series
```

## Query other objects

You can query images and other custom objects via the backend API. Check the `matyan_client.Repo` API for `query_metrics`, `query_runs`, and any object-specific query methods that mirror the backend endpoints.
