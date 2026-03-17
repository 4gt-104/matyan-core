---
icon: material/book-open
---

# Concepts

Matyan uses the same core concepts: runs, repo (backend), params, sequences, and context. Data lives server-side in FDB and S3, not in a local repo.

## Run

A **Run** represents one experiment/training run. In code it’s `matyan_client.Run`. You use it to:

- Set hyperparameters and other params (`run["hparams"] = {...}`).
- Track metrics and objects (`run.track(...)`).
- Add tags, set name/description, log artifacts and terminal output.

Runs are queryable and visible in the UI; each has a unique **hash**.

## Repo (backend)

**Repo** is the set of all runs (and related data) served by one backend. The client’s `Repo` object is a handle to that backend:

```python
from matyan_client import Repo

repo = Repo("http://localhost:53800")  # backend URL
for run in repo.iter_runs():
    ...
```

So “repo” in the docs and UI means “the set of runs (and related data) served by this backend.”

## Run params

Each run has **parameters**: hyperparameters, config, custom keys. You set them with a dict-like interface:

```python
run["hparams"] = {"lr": 0.001, "batch_size": 32}
run["custom_key"] = "value"
```

Params are stored in FDB and can be used in MatyanQL and for grouping in the UI.

## Run sequence

A **sequence** is an ordered list of values of the same kind (e.g. a metric series, or a sequence of images). It’s bound to a run and identified by **name** and **context**. When you call `run.track(value, name="loss", context={"subset": "train"})`, you’re appending to (or creating) the sequence `"loss"` with context `{"subset": "train"}`.

Sequences are typed (metric, image, audio, etc.). The UI and API represent them accordingly (charts, galleries, etc.).

## Sequence context

**Context** lets you have multiple sequences with the same name in one run. For example:

- `name="loss"`, `context={"subset": "train"}`
- `name="loss"`, `context={"subset": "val"}`

So the sequence is defined by (run, name, context). Context is a dict and is used in MatyanQL and the UI for filtering and grouping.
