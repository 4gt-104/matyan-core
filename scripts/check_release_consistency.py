#!/usr/bin/env python3
"""Pre-commit hook: validate release.yaml is consistent with Chart.yaml and values.yaml.

Run automatically by pre-commit on every commit. Exits non-zero with a descriptive
error message if any of the following conditions are violated when release.yaml is staged:

- Chart.yaml .version must equal release.yaml .helm.version
- values.yaml .backend.image.tag must equal release.yaml .images.backend
- values.yaml .ingestionWorker.image.tag must equal release.yaml .images.backend
- values.yaml .controlWorker.image.tag must equal release.yaml .images.backend
- values.yaml .frontier.image.tag must equal release.yaml .images.frontier
- values.yaml .ui.image.tag must equal release.yaml .images.ui

Each file is read from the staged index if it is staged, otherwise from the working tree.
This means unstaged files that already have the correct values are accepted without
needing to be re-staged alongside release.yaml.

Note: Chart.yaml .appVersion is intentionally not validated — it is set by CI from the
git tag and is not expected to be committed manually.
"""

import subprocess
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

RELEASE_CONFIG = "release.yaml"
CHART_YAML = "deploy/helm/matyan/Chart.yaml"
VALUES_YAML = "deploy/helm/matyan/values.yaml"


def get_staged_files() -> list[str]:
    """Return the list of files currently staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def get_file_content(path: str, staged: list[str]) -> str:
    """Return the effective content of a file for validation.

    Reads from the staged index when the file is staged; otherwise reads from the
    working tree. This allows files that are already correct and un-modified to pass
    validation without needing to be explicitly re-staged.

    :param path: Repo-relative path to the file.
    :param staged: List of currently staged file paths.
    :returns: File content as a string.
    :raises subprocess.CalledProcessError: If the file cannot be read.
    :raises FileNotFoundError: If the file does not exist in the working tree.
    """
    if path in staged:
        result = subprocess.run(
            ["git", "show", f":{path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    with open(path) as f:
        return f.read()


def main() -> int:
    """Run the release consistency check.

    :returns: 0 on success, 1 on validation failure.
    """
    staged = get_staged_files()

    if RELEASE_CONFIG not in staged:
        return 0

    errors: list[str] = []

    release = yaml.safe_load(get_file_content(RELEASE_CONFIG, staged))
    expected_chart_version: str = release["helm"]["version"]
    expected_backend: str = release["images"]["backend"]
    expected_frontier: str = release["images"]["frontier"]
    expected_ui: str = release["images"]["ui"]

    # Chart.yaml checks
    chart = yaml.safe_load(get_file_content(CHART_YAML, staged))
    actual_chart_version: str = chart.get("version", "")
    if actual_chart_version != expected_chart_version:
        errors.append(
            f"Chart.yaml .version '{actual_chart_version}' does not match "
            f"release.yaml .helm.version '{expected_chart_version}'."
        )

    # values.yaml checks
    values = yaml.safe_load(get_file_content(VALUES_YAML, staged))

    checks = [
        ("backend.image.tag", values["backend"]["image"]["tag"], expected_backend, "images.backend"),
        ("ingestionWorker.image.tag", values["ingestionWorker"]["image"]["tag"], expected_backend, "images.backend"),
        ("controlWorker.image.tag", values["controlWorker"]["image"]["tag"], expected_backend, "images.backend"),
        ("frontier.image.tag", values["frontier"]["image"]["tag"], expected_frontier, "images.frontier"),
        ("ui.image.tag", values["ui"]["image"]["tag"], expected_ui, "images.ui"),
    ]

    for values_path, actual, expected, release_path in checks:
        if actual != expected:
            errors.append(
                f"values.yaml .{values_path} '{actual}' does not match "
                f"release.yaml .{release_path} '{expected}'."
            )

    if errors:
        print("release consistency check FAILED:\n")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nEnsure all files are consistent before committing:\n"
            "  release.yaml, deploy/helm/matyan/Chart.yaml, deploy/helm/matyan/values.yaml"
        )
        return 1

    print("release consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
