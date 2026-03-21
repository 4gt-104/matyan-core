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
| **PyTorch Lightning** | `matyan_client.pytorch_lightning.MatyanLogger` | Pass as `trainer = Trainer(..., logger=aim_logger)`. Use `repo=` with backend URL. |
| **PyTorch Ignite** | `matyan_client.pytorch_ignite.MatyanLogger` | Attach output handlers to the trainer. |
| **Hugging Face** | `matyan_client.hugging_face.MatyanCallback` | Add to `Trainer(..., callbacks=[aim_callback])`. |
| **Keras / tf.Keras** | `matyan_client.keras.MatyanCallback` or `matyan_client.tensorflow.MatyanCallback` | Add to `model.fit(..., callbacks=[MatyanCallback(...)])`. |
| **XGBoost** | `matyan_client.xgboost.MatyanCallback` | Pass to `xgboost.train(..., callbacks=[MatyanCallback(...)])`. |
| **LightGBM** | `matyan_client.lightgbm.MatyanCallback` | Pass to `lgb.train(..., callbacks=[MatyanCallback(...)])`. |
| **CatBoost** | `matyan_client.catboost.MatyanLogger` | Pass to `model.fit(..., log_cout=MatyanLogger(...))`. |
| **Optuna** | `matyan_client.optuna.MatyanCallback` | Pass to `study.optimize(..., callbacks=[aim_callback])`. |
| **FastAI** | `matyan_client.fastai.MatyanCallback` | Pass to `cnn_learner(..., cbs=MatyanCallback(...))`. |
| **Stable-Baselines3** | `matyan_client.sb3.MatyanCallback` | Pass to `model.learn(..., callback=MatyanCallback(...))`. |

In all cases, use `repo="http://your-backend:53800"` (or the same URL via `MATYAN_BACKEND_URL`) so the adapter sends data to your Matyan backend and frontier.

For more detail, see the adapter source and examples in the `matyan-client` package (e.g. `extra/matyan-client/examples/` in the repo).

## What's next

While training, you can open the Matyan UI and watch runs in real time. See [Manage runs](../using/manage-runs.md) and [Query runs](../using/query-runs.md) for more.
