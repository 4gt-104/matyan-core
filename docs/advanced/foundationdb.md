---
icon: material/database-cog
---

# FoundationDB

**FoundationDB** (FDB) is the primary transactional store for Matyan. All run metadata, parameters, sequence metadata, time-series points (metrics, log lines, etc.), and secondary indexes live in FDB. It replaces the original stack’s RocksDB and SQLite with a single, scalable, transactional key-value layer.

## Role

- **Run and sequence data** — Runs, attrs, trace metadata, contexts, and sequence steps (metrics, params, log lines, log records) are stored as key-value pairs under a structured key space (directories/subspaces and tuples).
- **Structured entities** — Experiments, tags, dashboards, reports, notes, and their associations to runs are also in FDB.
- **Indexes** — Tier 1 indexes (archived, active, experiment, created_at, tag) and Tier 2 (scalar hyperparameters) are maintained in FDB and used by the query planner for MatyanQL run search.
- **Single source of truth** — The backend and ingestion/control workers all read and write FDB. There is no separate “metadata database”; one FDB cluster backs the whole system.

## Architectural decisions

### Why FoundationDB (not RocksDB or SQLite)

The original stack used **RocksDB** (per-run containers, Cython) and **SQLite** (experiments, tags, etc.). Matyan consolidates on **FDB** because:

- **Single cluster, multi-run** — All runs live in one FDB cluster with keys prefixed by run hash. Cross-run queries (e.g. “all runs in experiment X”) do not require opening many files; they are range scans over one key space.
- **Transactions** — FDB provides ACID transactions. Index updates (e.g. add run to experiment index, update hparam index) can be done in the same transaction as the primary write, so indexes stay consistent without a separate commit protocol.
- **Scalability** — FDB scales out (sharding, replication) and is designed for high write and read throughput. RocksDB is single-node; SQLite is single-writer. FDB fits a shared, multi-tenant backend.
- **No Cython** — The original storage used Cython for performance. FDB’s Python bindings are already C-backed; we can keep the storage layer in pure Python and still get good performance.
- **Operational familiarity** — FDB is run as a separate cluster (like Kafka or S3); operators can size, back up, and upgrade it independently. No embedded process inside the app.

### Key space design (tuples and subspaces)

Keys are built from **tuples** (using `fdb.tuple.pack`) and **subspaces** (prefixes). The layout mirrors the original Aim key structure so that the logical model (runs, attrs, traces, sequences) maps cleanly:

- **Run data** — e.g. `(run_hash, 'attrs', 'hparams', 'lr')`, `(run_hash, 'traces', ctx_id, 'loss', 'last')`, `(run_hash, 'seqs', 'v2', ctx_id, 'loss', 'val', step_hash)`. Runs are under a top-level “runs” directory; the rest is tuple-encoded paths.
- **Indexes** — e.g. `('experiment', name, run_hash)`, `('archived', bool, run_hash)`, `('tag', tag_name, run_hash)`, `('hparam', param_path, value, run_hash)`. Stored under an “indexes” directory. Values are often empty; the key itself is the index entry.
- **System** — e.g. schema version, cluster metadata under a “system” directory.

Using tuples (instead of a custom `\xfe`-style encoding) gives a standard, well-documented encoding and range-scan semantics (e.g. “all keys with prefix run_hash” or “all index entries for experiment X”).

### Index maintenance at write time

Tier 1 and Tier 2 indexes are updated **in the same FDB transaction** as the primary write (e.g. create run, set attrs, set experiment). So when an ingestion worker creates a run or sets hparams, it also writes the corresponding index entries. There is no eventual “indexer” job that scans FDB later; indexes are **write-time consistent**. Control workers (or the backend) update or remove index entries when runs are deleted, experiments renamed, or tags removed, again in transaction with the mutation.

### Query execution: index scan + filter

MatyanQL run search is implemented by:

1. **Planner** — Parse the query and identify predicates that map to indexes (e.g. `experiment == "baseline"`, `run.hparams.lr == 0.001`).
2. **Index scan** — Use the most selective index to get candidate run hashes (e.g. range scan on `('experiment', 'baseline', ...)`).
3. **Filter** — Load run data for candidates and evaluate remaining predicates in memory (RestrictedPython). This keeps index usage simple (equality/range on indexed fields) and allows arbitrary expressions on the filtered set.

### No schema layer on top of FDB

Matyan does not use FDB’s record layer or a SQL engine. The storage layer is **key-value with a fixed key layout**. Schema evolution is handled by a version key (e.g. in the system subspace) and, if needed, dual-read compatibility and background migration. There is no ORM; the code explicitly encodes and decodes values (e.g. msgpack with datetime extension) and knows the key structure.

### Transaction size and batching

FDB has transaction size and time limits (e.g. 10 MB, 5 seconds). Ingestion workers batch writes into transactions of reasonable size; large metric arrays or many steps may be split across multiple transactions per run to stay under limits. This is an operational and code constraint that the storage and worker design respect.

## Related

- [Backend](backend.md) — Reads from FDB; writes control state to FDB.
- [Workers](workers.md) — Ingestion workers write run/sequence data to FDB; control workers may read for context.
- [Data storage](../understanding/data-storage.md) — User-facing summary of where data lives.
