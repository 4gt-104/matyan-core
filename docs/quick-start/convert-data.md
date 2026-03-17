---
icon: material/swap-horizontal
---

# Migrate from other tools

You may have existing experiment logs from TensorBoard, MLflow, or Weights & Biases. Matyan provides a built-in **TensorBoard** converter in the client; for other tools you can use custom scripts or the public API.

## TensorBoard

TensorBoard conversion lives in **matyan-client**. It reads TensorBoard event logs and produces a **Matyan backup archive** (same format as backend backups). You can then restore that archive with the client or backend (see [Backups and restore](../using/backups-and-restore.md)).

**CLI (from matyan-client):**

```bash
matyan convert tensorboard <input_dir> <output_path> [--experiment NAME] [--compress] [--workers N]
```

- **input_dir** — Directory containing TensorBoard run directories (each with event files).
- **output_path** — Directory where the backup will be created (a timestamped subdirectory is added). Use `--compress` to produce a `.tar.gz` archive instead.
- **--experiment** — Optional; assign all converted runs to this experiment name.
- **--compress** — Produce a single `.tar.gz` archive.
- **--workers** — Number of parallel workers (default: CPU count).

After conversion, restore the backup with `matyan restore-reingest` (client) or `matyan-backend restore` (backend), as described in [Backups and restore](../using/backups-and-restore.md).

For image and audio events, the converter uses `tbparse`; TensorFlow is optional (install with `uv sync --extra convert` in matyan-client if you need image/audio support).

## MLflow / Weights & Biases

There is no built-in `matyan convert mlflow` or `matyan convert wandb`. Export your runs (metrics, params, artifacts) and either:

- Write a Python script that uses `matyan_client.Run` and `track()` to recreate runs, or
- Produce a Matyan backup directory (manifest + runs + entities) and use the same restore tools.

For large migrations, batching and async ingestion (via the frontier) will help.

## Other options

- **Re-track with Matyan** — Run your training (or a short replay) and log to Matyan using the same SDK patterns. Best when you can re-run or have a small dataset.
- **Future converters** — Community or project-specific converters may be added later; check the repository for updates.
