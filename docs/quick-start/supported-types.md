---
icon: material/format-list-checks
---

# Track media and objects

Matyan supports metrics, params, and rich types (images, audio, text, figures, distributions). Use the **matyan_client** package.

## Params and built-in types

`Run` params support Python built-in types (`int`, `float`, `bool`, `str`, `bytes`) and nested dictionaries, lists, and tuples. You can also use [OmegaConf](https://github.com/omry/omegaconf) configs.

## Objects and sequences

Tracking uses `run.track(value, name=..., step=..., context=...)`. Supported object types:

| Type | Import | Description |
|------|--------|-------------|
| **Metrics** | — | Scalars via `run.track(value, name="loss", step=step, context={...})`. |
| **Distribution** | `matyan_client.Distribution` | Histogram / distribution. |
| **Image** | `matyan_client.Image` | Images (file path, PIL, numpy, torch/tf tensor). |
| **Audio** | `matyan_client.Audio` | Audio (file path, bytes, numpy WAV). |
| **Text** | `matyan_client.Text` | Text strings. |
| **Figure** | `matyan_client.Figure` | Plotly or matplotlib figures. |

### Track multiple values at once

```python
run.track(
    {"accuracy": 0.72, "loss": 0.05},
    context={"subset": "train"},
    step=10,
    epoch=1,
)
```

### Distribution

```python
from matyan_client import Run, Distribution

run = Run(experiment="demo")
d = Distribution(distribution=[...], bin_count=64)
run.track(d, name="dist", step=0)
```

### Image

```python
from matyan_client import Run, Image

run = Run(experiment="demo")
img = Image("path/to/image.png", caption="sample")
run.track(img, name="images", step=step)
```

Supports: path, PIL Image, numpy array, torch/tf tensor, matplotlib figure. Optional: `caption`, `format`, `quality`, `optimize`.

### Audio

```python
from matyan_client import Run, Audio

run = Run(experiment="demo")
audio = Audio("path/to/audio.wav", format_="wav", caption="sample")
run.track(audio, name="audios", step=step)
```

### Text

```python
from matyan_client import Run, Text

run = Run(experiment="demo")
run.track(Text("some message"), name="text", step=step)
```

### Figure

```python
from matyan_client import Run, Figure
import plotly.express as px

run = Run(experiment="demo")
fig = px.bar(x=["a", "b", "c"], y=[1, 3, 2])
run.track(Figure(fig), name="figures", step=0)
```

Matplotlib figures are also supported (converted via Plotly under the hood).

## Artifacts

Use `run.log_artifact(path)` or `run.log_artifacts(directory)` to log files. Matyan stores artifact metadata and uses presigned S3 URLs (via the frontier) for blob uploads. See [Artifacts](../using/artifacts.md).
