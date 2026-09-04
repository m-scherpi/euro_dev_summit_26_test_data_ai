# Portal Publishing

> **Status: not started yet.** The folder is prepared and the reviewed plan sits
> in [`input/implementation_plan.md`](input/implementation_plan.md); no code has
> been written. Part of
> [Test (Geo-)Data Generation with GenAI](../README.md).

## Purpose

A fictional rent-price census for Münster — 500 generated points carrying rent
per square metre, median age, building type and household size — published to an
ArcGIS **Enterprise** Portal as a **Hosted Feature Layer**, and from there into a
**Web Map with four operational layers on that one layer**, each with its own
generated renderer:

```
seeded generator → CSV → Hosted Feature Layer → Web Map (4 layers, 4 renderers)
```

This is the one use case in the repository whose subject is not the data. The
other four stop at the data layer; this one asks how far into the platform
generated content can reach — item, service, schema, symbology, map. The data is
fictitious by construction, which is the point: it is the data set nobody is
allowed to have.

Two deliberate inversions of findings this repository made elsewhere, stated here
so it does not read as a contradiction:

- `opensearch` publishes a web feature layer that **references** registered data
  and copies nothing. This use case is the opposite — **copy all data**, rows
  living in the ArcGIS Data Store.
- `egdb_import` refused `GIS.content.import_data()` *because* it copies rows out
  of a database into a hosted layer. Here that copy is the deliverable. Same
  measurement, opposite verdict.

## Coordinate reference systems

_tbd — EPSG:4326 in the CSV, and the hosted layer stores EPSG:3857 metres
because `targetSR` defaults to WKID 102100. Both codes get named, and the extent
check states which unit it measured._

## Stack

_tbd — Python 3.12 stdlib for generation, verification and item building, so the
whole design is reviewable without a portal; a local venv with `arcgis` 2.4.1.1
for the two stages that need one._

## Input

`input/` — read-only source data.

| File | Description |
|---|---|
| `implementation_plan.md` | the reviewed plan for this use case, incl. the measured API findings it rests on |
| _district fixture, census fixtures, connection template_ | _tbd_ |

## Output

`output/` — generated artifacts only, always reproducible from `input/` plus the
documented command. Safe to delete entirely.

| File | Description |
|---|---|
| _none yet_ | — |

## Credentials

_tbd — password from `PORTAL_PASSWORD` or `--password`, no default and no
committed value. The `opensearch` throwaway-credential exception is deliberately
**not** taken: a real Enterprise Portal is a real system with a real account._

## Setup

```bash
# tbd
```

## Usage

```bash
# tbd — copy-pasteable example command
```

## Verification

_tbd — two offline checks (axis order and range; an independent EPSG:3857
recomputation) and four against the portal (field types survived the publish,
count and extent, four operational layers with four renderer types, items typed
and shared as intended). The depth was agreed up front rather than defaulted to:
plausible is enough for invented data, measured for what the portal did to it._

## Reproducibility

- Seed: _tbd (planned: `20260904`)_
- Model / date: plan written with Claude Opus 5, 2026-09-04
- Exact command that produced the committed output: _tbd_

## Notes for the talk

Measured while planning, before a line of code:

- **There is no Web Map class in the pinned client.** `arcgis` 2.4.1.1 has no
  `arcgis.map` module and no `arcgis.mapping.WebMap`; the wheel's `RECORD` lists
  zero `arcgis/map/` entries. The widely-repeated migration note "`WebMap` moved
  to `arcgis.map.Map`" is half true — the old class is gone, the new one is not
  shipped. Hand-built Web Map JSON is therefore the only route, not a workaround.
- **There is no published dashboard specification**, and the bundled builder API
  is deprecated and cannot produce the one widget a dashboard needs most, the map
  widget. It remains usable offline as a first-party oracle for the other widget
  shapes. The dashboard stage is deferred for that reason.
- **What failed:** _tbd_
- **Lesson learned:** _tbd_
