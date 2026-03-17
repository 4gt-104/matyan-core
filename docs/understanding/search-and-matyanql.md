---
icon: material/magnify
---

# Search and MatyanQL

**MatyanQL** is the query language for filtering runs, metrics, and custom objects (images, audios, texts, distributions, figures) in the UI and API. This page is the single reference: **Quick reference** below gives syntax and examples by tab; **Reference** explains the pipeline, property tables, and why some queries are fast or slow.

---

## Quick reference

### How it works

- MatyanQL is a **single Python expression** evaluated in a boolean context (like an `if` condition).
- The expression is evaluated for each candidate (run, or run+sequence). If it is truthy, the entity is included.
- Queries are **filter-only**; they do not define sorting or aggregation.
- An optional **`SELECT ... IF <expr>`** prefix is stripped; you can also write the condition directly.
- If you do **not** mention `run.is_archived` or `run.archived`, the backend automatically adds **`run.is_archived == False`** so archived runs are hidden by default.

### Which namespaces in which tab

| Tab / context   | Namespaces you can use | Use for |
|-----------------|------------------------|--------|
| **Runs**        | `run` only             | Filter by run properties and hyperparameters. |
| **Metrics**     | `run`, `metric`        | Filter by run and by metric name/context/last. |
| **Images**      | `run`, `images`        | Filter by run and by image sequence name/context. |
| **Audios**      | `run`, `audios`        | Same with `audios`. |
| **Texts**       | `run`, `texts`         | Same with `texts`. |
| **Distributions** | `run`, `distributions` | Same with `distributions`. |
| **Figures**    | `run`, `figures`       | Same with `figures`. |

Use the namespace that matches the tab (e.g. `metric` on Metrics, `images` on Images). Full property lists are in the [Reference](#run-namespace-run) section below.

### Run search (Runs tab)

Use the **`run`** namespace. Common properties: `run.hash`, `run.name`, `run.experiment`, `run.tags`, `run.is_archived`, `run.active`, `run.created_at`, `run.duration`, `run.hparams.<name>`.

**Examples (indexed — fast):**

```text
run.experiment == "baseline"
"production" in run.tags
run.hparams.lr > 0.0001
run.hparams.batch_size == 32
```

**Examples (not indexed — can be slow):**

```text
run.duration > 60
run.created_at >= datetime(2026, 3, 1)
run.experiment == "baseline" and run.duration > 10
```

### Metric search (Metrics tab)

Use **`run`** and **`metric`** (`metric.name`, `metric.context`, `metric.last`, `metric.last_step`). Only **`metric.name == "literal"`** is index-backed.

**Examples:**

```text
metric.name == "loss"
run.experiment == "baseline" and metric.name == "accuracy"
metric.name == "loss" and metric.context.subset == "train"
```

### Custom object search (Images, Audios, Texts, etc.)

Use **`run`** and the tab’s namespace: **`images`**, **`audios`**, **`texts`**, **`distributions`**, or **`figures`**. Same shape as `metric`: **name**, **context**, **last**, **last_step**.

**Examples:**

```text
run.experiment == "exp1" and images.name == "samples"
audios.name == "waveform" and run.active == True
```

### Why some queries are fast and others slow (summary)

- **Very fast:** Only index-backed predicates (e.g. `run.experiment == "x"`, `run.hparams.lr == 0.001`, `"tag" in run.tags`, `metric.name == "loss"`).
- **Slower:** At least one non-indexed predicate; backend may still use an index for a subset then filter in memory.
- **Slow (full scan):** No index-backed predicate, or OR with an unindexed branch.

See [Index-backed predicates](#index-backed-predicates-why-some-queries-are-fast) below for the full list.

### Security

MatyanQL is evaluated with [RestrictedPython](https://github.com/zopefoundation/RestrictedPython): only a safe subset of Python is allowed. User-written queries cannot execute arbitrary code.

---

## Reference

### Pipeline overview

When you submit a MatyanQL string (e.g. in the Search box or via the run/metric search API), the backend runs a fixed pipeline:

1. **String normalization** — Optional `SELECT ... IF <expr>` prefix is stripped; the result is wrapped in parentheses. Empty input is treated as "show non-archived runs."
2. **Default predicate** — Unless the query already mentions `run.is_archived` or `run.archived`, the backend **AND**s the expression with `run.is_archived == False` so archived runs are hidden by default.
3. **Parse** — The string is parsed into a Python **AST** (abstract syntax tree) with `compile(..., mode="eval")`. Invalid syntax raises `SyntaxError` (e.g. 400 to the UI).
4. **AST rewrites** — Two rewrites run on the AST:
   - **datetime(...)** — Replaced with a numeric UTC timestamp using the request's timezone offset (`x_timezone_offset`), so e.g. `datetime(2026, 3, 10) <= run.created_at` becomes a float comparison.
   - **Chained comparisons** — `a <= b < c` is split into `(a <= b) and (b < c)` so the planner can match each half against index patterns.
5. **Planner** — The prepared AST is passed to **plan_query(db, prepared_ast)**. The planner walks the AST and matches **index-backed predicates** (experiment, tag, archived, active, hparams, metric.name). It returns:
   - **PlanResult(candidates, exact, trace_names)**
   - `candidates`: list of run hashes from index(es), or **None** for "no index use" (full scan).
   - `exact`: if True, every candidate satisfies the full query; if False, candidates are a **superset** and the backend must run **RestrictedPythonQuery.check()** on each.
   - `trace_names`: when the query has `metric.name == "..."`, the set of metric names to stream; **None** means "all traces."
6. **Execution** — Depending on the endpoint (run search, metric search, or custom-object search):
   - If **candidates** is a list and **exact** is True: iterate only those hashes (no per-run filter).
   - If **candidates** is a list and **exact** is False: iterate candidates, load run (and optionally sequence) data, and call **q.check(run=..., metric=...)** (or the right namespace) to filter.
   - If **candidates** is **None**: **lazy path** — iterate **all** run hashes from the **created_at** index (no predicate index), load each run (and sequences if needed), and call **q.check()** for each. This is a full scan.
7. **Security** — The expression is compiled with **RestrictedPython**: only a safe subset of Python is allowed (no file access, no arbitrary imports). The only allowed namespaces are `run`, `metric`, and the custom-object names (`images`, `audios`, `distributions`, `figures`, `texts`), plus builtins like `datetime`, `min`, `max`, `sorted`, etc.

### Namespaces and which tab uses them

MatyanQL expressions can reference one or more **namespaces**. The backend passes only the namespaces that exist in the current context; referencing a namespace that wasn't passed (e.g. `metric` on the Runs tab) makes that part of the expression evaluate against a missing name and can lead to errors or no matches.

| UI / API context        | Namespaces passed to `check()` | Typical use |
|-------------------------|---------------------------------|-------------|
| **Runs** tab / run search | `run` only | Filter by run properties and hyperparameters. |
| **Metrics** tab / metric search | `run`, `metric` | Filter by run and by metric name/context/last. |
| **Images** tab           | `run`, `images` | Filter by run and by image sequence name/context. |
| **Audios** tab           | `run`, `audios` | Same with `audios`. |
| **Texts** tab            | `run`, `texts` | Same with `texts`. |
| **Distributions** tab    | `run`, `distributions` | Same with `distributions`. |
| **Figures** tab          | `run`, `figures` | Same with `figures`. |

In every **sequence** context (metrics, images, audios, etc.), the second namespace is a **sequence view** with the same shape: **name**, **context** (dict-like), **last**, **last_step**.

### Run namespace (`run`)

Available in **all** tabs. Properties (and examples) include:

| Property        | Type / notes | Example |
|-----------------|--------------|---------|
| `run.hash`      | str          | `run.hash == "abc123"` |
| `run.name`      | str          | `run.name != ""` |
| `run.experiment`| str or None  | `run.experiment == "baseline"` |
| `run.tags`      | container    | `"production" in run.tags` |
| `run.archived` / `run.is_archived` | bool | `run.is_archived == False` (default) |
| `run.active`    | bool         | `run.active == True` |
| `run.created_at`| float (timestamp) | `run.created_at >= datetime(2026, 3, 10)` |
| `run.duration`  | float        | `run.duration > 60` |
| `run.hparams.<name>` | any (top-level scalar) | `run.hparams.lr > 0.001` |
| `run["hparams"]["<name>"]` | same | `run["hparams"]["batch_size"] == 32` |

Hyperparameters are only **indexed** when they are **top-level scalar** attributes under `hparams` (e.g. `run.hparams.lr`, not nested objects). Dot and bracket syntax are both supported for indexing.

### Metric namespace (`metric`)

Available only in the **Metrics** tab (and metric search API). Use **`metric`** in the expression.

| Property         | Type / notes | Example |
|------------------|--------------|---------|
| `metric.name`    | str          | `metric.name == "loss"` |
| `metric.context` | dict-like    | `metric.context.subset == "train"` |
| `metric.last`    | last value   | `metric.last >= 0.5` |
| `metric.last_step` | int or None | `metric.last_step > 100` |

Only **`metric.name == "literal"`** is index-backed (Tier 3 trace-name index). All other metric conditions (context, last, last_step, or `metric.name.startswith(...)`) are **not** indexed: the planner cannot use them to narrow candidates, so the backend may still scan runs/traces and filter in memory.

### Custom-object namespaces (`images`, `audios`, `texts`, `distributions`, `figures`)

Same shape as **metric**: **name**, **context**, **last**, **last_step**. Use the name that matches the tab (e.g. `images` on Images tab). There is **no** index on sequence name or context for custom objects — filtering by `images.name == "x"` or `run.experiment == "y"` uses the run-level index for `run.experiment` and then filters sequences in memory.

### Index-backed predicates (why some queries are fast)

The planner only recognizes the following patterns. Anything else does **not** contribute to `candidates` and can force a full scan or a superset + filter.

| Predicate shape | Index | Notes |
|-----------------|-------|--------|
| `run.experiment == "name"` | Tier 1 (experiment) | Exact experiment name. |
| `"tag" in run.tags` | Tier 1 (tag) | Run has this tag. |
| `run.active == True` or `False` | Tier 1 (active) | Live vs finished. |
| `run.is_archived == True` or `False` (or `run.archived`) | Tier 1 (archived) | Archived flag. |
| `run.hash == "hash"` | — | Single run by hash. |
| `run.hparams.<name> == <val>` | Tier 2 (hparam) | Top-level scalar hparam equality. |
| `run.hparams.<name> < \| <= \| > \| >= <val>` | Tier 2 (hparam range) | Range on top-level scalar hparam. |
| `run["hparams"]["<name>"]` same ops | Tier 2 | Bracket form. |
| `metric.name == "name"` | Tier 3 (trace name) | Only in metric search; restricts which traces are streamed. |

**Not indexed** (so they don't narrow the candidate set; used only in `check()`):

- `run.name`, `run.description`, `run.created_at`, `run.duration`, `run.tags.contains(...)` (other than `in run.tags` for a single tag)
- `metric.context.*`, `metric.last`, `metric.last_step`, `metric.name.startswith(...)`, or any non-equality on `metric.name`
- Any predicate that the planner doesn't match (e.g. complex expressions, method calls that aren't one of the above)

**AND** logic: if the query is `A and B` and both A and B are index-backed, the planner **intersects** the candidate sets → often very fast. If only A is index-backed, the planner returns candidates for A with `exact=False`, and the backend loads each run and runs `check()` to apply B.

**OR** logic: if **any** branch of an OR is not index-backed, the planner returns **None** (full scan). So `run.experiment == "a" or run.name == "b"` cannot use the experiment index and falls back to the lazy path.

### Why some queries are fast and others slow (detailed)

- **Very fast (index-only, exact)**  
  Query uses **only** index-backed predicates and the planner can resolve the full expression (e.g. `run.experiment == "baseline" and run.hparams.lr == 0.001`). The backend iterates only the returned run hashes and does **not** call `check()`. No per-run meta or attrs load for filtering.

- **Fast (index superset + filter)**  
  Query mixes index-backed and non-indexed predicates (e.g. `run.experiment == "baseline" and run.name != ""`). The planner returns candidates for `experiment == "baseline"` with `exact=False`. The backend iterates only those hashes but **loads** run meta (and optionally traces) and runs **check()** for each. Slower than exact path but still only touches a subset of runs.

- **Slow (full scan / lazy path)**  
  Query has **no** index-backed predicate, or has an **OR** with at least one unindexed branch, or uses only run properties that are not in the planner (e.g. `run.created_at > X`, `run.duration > 10`, `run.name.startswith("x")`). The planner returns **candidates=None**. The backend iterates **all** run hashes from the **created_at** index, loads each run (and for metric/custom-object search, all traces), and runs **check()** for each. Time is proportional to total runs (and total traces in metric/object search).

- **Metric search: unindexed sequence predicate**  
  If the query uses `metric.context`, `metric.last`, or `metric.name.startswith(...)` (or any non–index-backed metric condition), the backend **resets** the candidate list to **None** for metric search and uses the lazy path so that every run and trace is considered. So even if `run.experiment == "x"` is indexed, adding `metric.context.subset == "train"` forces a full scan for that request.

Summary: **prefer index-backed predicates** (experiment, tag, active, archived, top-level hparam equality/range, and for metrics `metric.name == "..."`). Avoid relying only on `run.created_at`, `run.duration`, `run.name`, or metric context/last in hot paths; combine them with at least one indexed predicate when possible.

### Security and builtins

MatyanQL is compiled and executed with **RestrictedPython**. Only a restricted set of builtins is available (e.g. `datetime`, `timedelta`, `min`, `max`, `sum`, `sorted`, `any`, `all`). Attribute access is guarded (e.g. no `format` on strings, no attributes starting with `_`). This prevents arbitrary code execution from the query string.
