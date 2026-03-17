---
icon: material/connection
---

# Integrate Matyan into your project

Use the Matyan client in any Python script or with your ML framework. Point `Run` and `Repo` at your Matyan **frontier** and **backend** URLs.

## Any Python script

Use `Run(experiment=...)`, `run["hparams"]`, `run.track()`, and `run.close()` as in [Getting started](../getting-started.md). Set `MATYAN_FRONTIER_URL` and `MATYAN_BACKEND_URL`, or pass the backend URL to `Run(repo="http://backend:53800")`. The framework adapters below use the same API.

## Framework integrations

Matyan provides framework adapters for popular ML libraries. Import from `matyan_client`:

| Framework | Adapter | Usage |
|-----------|---------|--------|
| **PyTorch Lightning** | `matyan_client.pytorch_lightning.AimLogger` | Pass as `trainer = Trainer(..., logger=aim_logger)`. Use `repo=` with backend URL. |
| **PyTorch Ignite** | `matyan_client.pytorch_ignite.AimLogger` | Attach output handlers to the trainer. |
| **Hugging Face** | `matyan_client.hugging_face.AimCallback` | Add to `Trainer(..., callbacks=[aim_callback])`. |
| **Keras / tf.Keras** | `matyan_client.keras.AimCallback` or `matyan_client.tensorflow.AimCallback` | Add to `model.fit(..., callbacks=[AimCallback(...)])`. |
| **XGBoost** | `matyan_client.xgboost.AimCallback` | Pass to `xgboost.train(..., callbacks=[AimCallback(...)])`. |
| **LightGBM** | `matyan_client.lightgbm.AimCallback` | Pass to `lgb.train(..., callbacks=[AimCallback(...)])`. |
| **CatBoost** | `matyan_client.catboost.AimLogger` | Pass to `model.fit(..., log_cout=AimLogger(...))`. |
| **Optuna** | `matyan_client.optuna.AimCallback` | Pass to `study.optimize(..., callbacks=[aim_callback])`. |
| **FastAI** | `matyan_client.fastai.AimCallback` | Pass to `cnn_learner(..., cbs=AimCallback(...))`. |
| **Stable-Baselines3** | `matyan_client.sb3.AimCallback` | Pass to `model.learn(..., callback=AimCallback(...))`. |

In all cases, use `repo="http://your-backend:53800"` (or the same URL via `MATYAN_BACKEND_URL`) so the adapter sends data to your Matyan backend and frontier.

For more detail, see the adapter source and examples in the `matyan-client` package (e.g. `extra/matyan-client/examples/` in the repo).

## What's next

While training, you can open the Matyan UI and watch runs in real time. See [Manage runs](../using/manage-runs.md) and [Query runs](../using/query-runs.md) for more.
