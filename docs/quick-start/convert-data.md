---
icon: material/swap-horizontal
---

# Migrate from other tools

You may have existing experiment logs from TensorBoard, MLflow, or Weights & Biases. Matyan provides a built-in **TensorBoard** converter in the client; for other tools you can use custom scripts or the public API.

## TensorBoard

TensorBoard conversion lives in **matyan-client**. It reads TensorBoard event logs and produces a **Matyan backup archive** (same format as backend backups). You can then restore that archive with the client or backend (see [Backups and restore](../using/backups-and-restore.md)).

**CLI:**

```bash
matyan-client convert tensorboard <input_dir> <output_path> [--experiment NAME] [--compress] [--workers N]
```

- **input_dir** — Directory containing TensorBoard run directories (each with event files).
- **output_path** — Directory where the backup will be created (a timestamped subdirectory is added). Use `--compress` to produce a `.tar.gz` archive instead.
- **--experiment** — Optional; assign all converted runs to this experiment name.
- **--compress** — Produce a single `.tar.gz` archive.
- **--workers** — Number of parallel workers (default: CPU count).

After conversion, restore the backup with `matyan-client restore-reingest` (client) or `matyan-backend restore` (backend), as described in [Backups and restore](../using/backups-and-restore.md).

For image and audio events, the converter uses `tbparse`; TensorFlow is optional (install with `uv sync --extra convert` in matyan-client if you need image/audio support).

## MLflow / Weights & Biases

There is no built-in `matyan-client convert mlflow` or `matyan-client convert wandb` yet. If you need this, please [open an issue on GitHub](https://github.com/4gt-104/matyan-client/issues) (check for an existing one first) so we can track demand and prioritize.

## Other options

- **Re-track with Matyan** — Run your training (or a short replay) and log to Matyan using the same SDK patterns. Best when you can re-run or have a small dataset.
- **Future converters** — Community or project-specific converters may be added later; check the repository for updates.
