---
icon: material/api
---

# Backend REST API

REST and streaming endpoints implemented by **matyan-backend**. All routes are under `/api/v1/rest` (or as configured). The following sections list the endpoint handler functions generated from the Python API modules.

## Runs (CRUD and logs)

Run lifecycle, metadata, tags, notes, logs, and artifact download.

::: matyan_backend.api.runs._run
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Runs (streaming search)

Run search, metric search, active runs, metric alignment, and metric batch. These endpoints use the binary streaming codec.

::: matyan_backend.api.runs._streaming
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Experiments

Experiment CRUD, runs listing, notes, and activity.

::: matyan_backend.api.experiments._main
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Tags

Tag CRUD and tagged runs listing.

::: matyan_backend.api.tags._main
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Projects

Project info, activity, params aggregation, and pinned sequences.

::: matyan_backend.api.projects._main
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Dashboards

::: matyan_backend.api.dashboards.views
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Dashboard apps

::: matyan_backend.api.dashboard_apps.views
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]

## Reports

::: matyan_backend.api.reports.views
    options:
      show_source: false
      show_root_heading: true
      filters: ["!^_"]
