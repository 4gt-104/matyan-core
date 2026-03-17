---
icon: material/script-text
---

# Log messages during training

Use the Matyan client’s logging API to send structured log messages to the run. They appear in the UI and are stored as run sequences.

## Logging API

The `Run` object exposes:

- **run.log_debug(msg)** — DEBUG level
- **run.log_info(msg)** — INFO level  
- **run.log_warning(msg)** — WARNING level
- **run.log_error(msg)** — ERROR level

Example:

```python
from matyan_client import Run

run = Run(experiment="demo")
run.log_info("Training started")
run.log_warning("Low learning rate")
run.log_error("Validation loss is NaN")
run.close()
```

Messages are sent to the frontier (like other tracking data) and stored by the ingestion workers. View them in the Matyan UI on the run detail page (e.g. Logs / structured log records).

## Notifications

To react to log messages, you can consume run log data via the backend API or build a custom subscriber to your own pipeline.
