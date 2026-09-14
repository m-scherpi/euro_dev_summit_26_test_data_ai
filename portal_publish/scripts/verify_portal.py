#!/usr/bin/env python3
"""Verify what the ArcGIS Enterprise Portal actually stored - four checks.

Four, and the number is a decision. `opensearch` earned twelve checks because
its data was real, published and attributed, and a wrong coordinate there would
have been a false claim about the world. Nothing here is real, so the questions
that made those twelve worth their cost do not exist. What is left is what the
*portal* did to a payload this repository wrote, which is the whole subject of
the use case:

    3. Field types survived the publish - ours, not the portal's guess.
    4. Count and extent, measured in the unit the layer actually stores.
    5. Four operational layers, four renderer types, one service.
    6. The items exist, are typed, tagged, and shared as intended.

They are numbered 3 to 6 because checks 1 and 2 are the offline ones in
`verify_census.py`. Six for the whole use case; the README lists the four
omissions with a sentence each, because an omission recorded as a decision is
not the same thing as an omission.

This script imports **nothing** from `census.py`. Every expectation is read as
data - the declared schema from `output/publish_parameters.json`, the bounding
box from `input/muenster_districts.json` - or restated here from a second
reading of the specification, which is the case for the four renderer types. A
checker that imports the declaration it is checking is comparing a constant
with itself.

Requires `arcgis` 2.4.1.1 - see `requirements.txt`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PASSWORD_ENV = "PORTAL_PASSWORD"
REDACTED = f"<{PASSWORD_ENV}>"

# EPSG:3857's sphere radius, restated from the coordinate system's definition.
EARTH_RADIUS_M = 6378137.0

# The renderers the web map must carry, as a count per type, restated from the
# Web Map Specification rather than imported from the builder. A set would no
# longer do: `classBreaks` appears twice on purpose - once on `median_age` and
# once on `rent_eur_sqm`, the latter as the readable counterpart to the heatmap
# drawn from the same column - and a set cannot tell a missing second
# class-breaks layer from a present one.
#
# `simple` is the one that needs a second condition: on its own it proves
# nothing, because a renderer whose visual variable was dropped is still a valid
# `simple` renderer drawing every point at the same size. So the size ramp is
# asserted separately.
EXPECTED_RENDERER_COUNTS = {
    "heatmap": 1, "classBreaks": 2, "uniqueValue": 1, "simple": 1,
}
EXPECTED_LAYER_COUNT = sum(EXPECTED_RENDERER_COUNTS.values())
EXPECTED_VISUAL_VARIABLE = "sizeInfo"

# How far above the largest weight a heatmap's `maxPixelIntensity` has to sit
# before the top colour means overlap rather than one feature. 1.5 is a
# judgement, stated here rather than buried in the check: it is loose enough
# that a deliberately tight calibration passes and tight enough that the
# unit-confusion defect - a ceiling *below* the largest weight - cannot.
HEATMAP_SATURATION_MARGIN = 1.5

# The only heatmap encoding ArcGIS Enterprise 12.1 actually draws. Not a
# preference: the current `radius`/`minDensity`/`maxDensity` form was published
# once, stored intact, and rendered as an empty layer while all four checks
# reported green. See `check_heatmap_ramp` for the table.
EXPECTED_HEATMAP_ENCODING = "gaussian"

# Esri field types a decimal column must never come back as. `esriFieldTypeSingle`
# is a 32-bit float with about seven significant decimal digits; a latitude of
# 51.96253 needs seven and an EPSG:3857 metre value needs ten. The rounding is
# silent and puts a plausible coordinate in the wrong place, which is why this is
# the one type failure worth failing the whole check over.
FORBIDDEN_FOR_DECIMALS = {"esriFieldTypeSingle"}

# Columns whose values look like numbers and are not - a code, an identifier, a
# label. `egdb_import` measured the cost of getting this wrong: `state_fips`
# holding `01`..`09` measures as an integer, and as a LONG it becomes `1`..`9`,
# after which a query for '01' finds nothing. This data set has no such column
# today, and the check is here anyway, because the next CSV will.
CODE_LIKE_COLUMNS = {"district", "building_type", "address"}
NUMERIC_ESRI_TYPES = {
    "esriFieldTypeSmallInteger", "esriFieldTypeInteger", "esriFieldTypeSingle",
    "esriFieldTypeDouble", "esriFieldTypeOID",
}

# The margin the extent check allows around the source bounding box, as a
# fraction of the box's own span. It exists because the box is the *sampling*
# domain and the extent is what the service reports for the features it holds -
# the two agree only up to the service's own rounding of its extent metadata.
# Deliberately generous: this check exists to catch a coordinate landing in the
# Gulf of Guinea, not to measure a metre.
EXTENT_MARGIN = 0.02


class VerifyError(Exception):
    """Something the verifier cannot check."""


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 degrees to EPSG:3857 metres - `y = R * atanh(sin phi)`.

    Needed only to express the expected bounding box in the unit the hosted
    layer stores. `targetSR` defaults to WKID 102100, so the layer holds
    **metres** even though every coordinate in the CSV is a degree, and an
    extent check that compares metres against degrees passes for the wrong
    reason: `egdb_import` measured what that looks like, with a hundred points
    inside 52 metres of 0 N 0 E in the Gulf of Guinea because a longitude of
    7.46 read as 7.46 metres is 0.000067 degrees.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.atanh(math.sin(math.radians(lat_deg)))
    return x, y


def connect(args: argparse.Namespace, password: str):
    """Open the portal connection. The only place `arcgis` is imported.

    `--ca-cert` reaches the library as `GIS(ca_bundles=...)`, not as
    `REQUESTS_CA_BUNDLE`: the adapter `arcgis` mounts builds its own
    `ssl.SSLContext`, so requests never reads the variable. Measured, with the
    full reasoning, in `publish_to_portal.connect`.
    """
    ca_bundle = None
    if args.ca_cert:
        ca_path = Path(args.ca_cert).resolve()
        if not ca_path.is_file():
            raise VerifyError(f"--ca-cert not found: {ca_path}")
        ca_bundle = str(ca_path)
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
    try:
        from arcgis.gis import GIS
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise VerifyError(
            f"arcgis is not importable ({exc}). This script needs it: unlike the "
            f"publisher's --dry-run it asks the portal what it stored, which cannot be "
            f"done offline."
        ) from None
    print(f"connecting to {args.portal} as {args.user} (password: {REDACTED})")
    kwargs = {"ca_bundles": ca_bundle} if ca_bundle else {}
    return GIS(
        args.portal, username=args.user, password=password,
        verify_cert=not args.no_verify_cert, **kwargs,
    )


# ---------------------------------------------------------------------------
# Check 3 - field types
# ---------------------------------------------------------------------------


def check_field_types(
    layer, declared: dict, guessed: dict | None, retrofit: dict | None = None
) -> dict:
    """Did our declaration survive the publish - and what would the portal have guessed?

    This is the one measurement worth having in this folder. The declared
    schema is read from `output/publish_parameters.json` as data; the portal's
    own guess, if `content.analyze` was recorded, is read from
    `output/analyze_publish_parameters.json` beside it. The comparison is
    three-way: what we declared, what the portal stored, and what the portal
    would have chosen if nobody had declared anything.

    **A mismatched TEXT length is reported and does not fail the check, and the
    demotion is a measurement rather than a convenience.** The first real
    publish stored all three declared `TEXT(80)`/`TEXT(40)` columns as
    `TEXT(8000)`. `updateDefinition` was then asked to set them afterwards and
    answered `{"success": true}` - after which the service still reports 8000.
    So there is nothing left to fix on this side: the platform sizes hosted
    string columns itself, and the API's confirmation is worthless. A check
    that can only ever be red stops carrying information, so the finding moves
    to where a finding belongs, with the API's claim printed next to the
    measurement that contradicts it. CLAUDE.md: check what an API wrote, not
    whether it threw - and here, not whether it said it did.

    The *types* still fail the check, and that is the claim this use case makes.
    """
    stored = {
        field["name"]: field
        for field in layer.properties.fields
        if field["name"] not in ("OBJECTID", "objectid", "Shape", "SHAPE")
    }
    declared_fields = {
        field["name"]: field for field in declared["layerInfo"]["fields"]
    }
    guessed_fields = {}
    if guessed:
        layer_info = guessed.get("layerInfo") or {}
        guessed_fields = {f["name"]: f for f in layer_info.get("fields", [])}

    rows = []
    failures: list[str] = []
    length_findings: list[str] = []
    for name, want in declared_fields.items():
        got = stored.get(name)
        guess = guessed_fields.get(name)
        entry = {
            "field": name,
            "declared": want["type"],
            "declared_length": want.get("length"),
            "stored": got["type"] if got else None,
            "stored_length": got.get("length") if got else None,
            "portal_guess": guess["type"] if guess else None,
        }
        if got is None:
            failures.append(f"{name}: declared {want['type']} and absent from the layer")
        else:
            if got["type"] != want["type"]:
                failures.append(
                    f"{name}: declared {want['type']}, stored {got['type']}"
                )
            if want.get("length") and got.get("length") and got["length"] != want["length"]:
                length_findings.append(
                    f"{name}: declared TEXT({want['length']}), stored "
                    f"TEXT({got['length']})"
                )
            if want["type"] == "esriFieldTypeDouble" and got["type"] in FORBIDDEN_FOR_DECIMALS:
                failures.append(
                    f"{name}: came back as {got['type']}, which carries about seven "
                    f"significant decimal digits - silent rounding of a coordinate"
                )
            if name in CODE_LIKE_COLUMNS and got["type"] in NUMERIC_ESRI_TYPES:
                failures.append(
                    f"{name}: is a code or a label and came back numeric ({got['type']})"
                )
        rows.append(entry)

    unexpected = sorted(set(stored) - set(declared_fields))
    if unexpected:
        failures.append(
            f"the layer carries undeclared fields: {', '.join(unexpected)}"
        )

    disagreements = [
        r for r in rows
        if r["portal_guess"] is not None and r["portal_guess"] != r["declared"]
    ]
    retrofit_claim = None
    if retrofit is not None:
        if retrofit.get("raised"):
            retrofit_claim = f"refused: {retrofit['raised']}"
        else:
            retrofit_claim = f"reported {json.dumps(retrofit.get('response'))}"

    return {
        "name": "Field types survived the publish",
        "passed": not failures,
        "failures": failures,
        "info": length_findings,
        "retrofit_claim": retrofit_claim,
        "rows": rows,
        "guess_disagreements": disagreements,
        "guess_available": bool(guessed_fields),
    }


# ---------------------------------------------------------------------------
# Check 4 - count and extent
# ---------------------------------------------------------------------------


def check_count_and_extent(layer, expected_count: int, box: dict) -> dict:
    """Feature count, and an extent check that says which unit it measured.

    The unit is the whole point. `targetSR` was declared as WKID 102100, so the
    layer stores metres; the expected box comes from `input/` in degrees and is
    projected here to compare like with like. The check reports the layer's own
    reported spatial reference, so a future run against a layer in degrees does
    not silently compare degrees against metres and pass.
    """
    count = layer.query(where="1=1", return_count_only=True)
    extent = dict(layer.properties.extent)
    spatial_reference = dict(extent.get("spatialReference") or {})
    wkid = spatial_reference.get("latestWkid") or spatial_reference.get("wkid")

    lat_min = float(box["latitude_min"])
    lat_max = float(box["latitude_max"])
    lon_min = float(box["longitude_min"])
    lon_max = float(box["longitude_max"])

    if wkid in (3857, 102100):
        unit = "metres (EPSG:3857)"
        x_min, y_min = lonlat_to_web_mercator(lon_min, lat_min)
        x_max, y_max = lonlat_to_web_mercator(lon_max, lat_max)
    elif wkid == 4326:
        unit = "degrees (EPSG:4326)"
        x_min, y_min, x_max, y_max = lon_min, lat_min, lon_max, lat_max
    else:
        return {
            "name": "Count and extent",
            "passed": False,
            "failures": [
                f"the layer reports spatial reference {spatial_reference!r}, which this "
                f"check does not know how to express the expected box in. Refusing to "
                f"compare numbers whose unit is unknown - that is exactly how a point in "
                f"the Gulf of Guinea passes an extent check."
            ],
            "count": count,
            "extent": extent,
            "unit": "unknown",
        }

    pad_x = (x_max - x_min) * EXTENT_MARGIN
    pad_y = (y_max - y_min) * EXTENT_MARGIN
    bounds = {
        "expected_xmin": x_min - pad_x, "expected_ymin": y_min - pad_y,
        "expected_xmax": x_max + pad_x, "expected_ymax": y_max + pad_y,
    }

    failures = []
    if count != expected_count:
        failures.append(f"the layer holds {count} features, expected {expected_count}")
    for key, low, high in (
        ("xmin", bounds["expected_xmin"], bounds["expected_xmax"]),
        ("xmax", bounds["expected_xmin"], bounds["expected_xmax"]),
        ("ymin", bounds["expected_ymin"], bounds["expected_ymax"]),
        ("ymax", bounds["expected_ymin"], bounds["expected_ymax"]),
    ):
        value = float(extent[key])
        if not low <= value <= high:
            failures.append(
                f"extent.{key} = {value:,.2f} is outside the expected "
                f"{low:,.2f}..{high:,.2f} - measured in {unit}"
            )

    return {
        "name": "Count and extent",
        "passed": not failures,
        "failures": failures,
        "count": count,
        "expected_count": expected_count,
        "extent": extent,
        "expected_bounds": bounds,
        "unit": unit,
        "wkid": wkid,
    }


# ---------------------------------------------------------------------------
# Check 5 - the web map
# ---------------------------------------------------------------------------


def read_numeric_columns(csv_path: Path) -> dict[str, list[float]]:
    """Every column of the source CSV that parses as a number, end to end.

    Only used to answer one question the web map cannot answer about itself:
    what a single feature weighs. A heatmap's intensity ramp is meaningless
    without it.
    """
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns: dict[str, list[float]] = {}
    for name in rows[0] if rows else {}:
        try:
            columns[name] = [float(row[name]) for row in rows]
        except ValueError:
            continue
    return columns


def check_heatmap_ramp(renderer: dict, columns: dict[str, list[float]]) -> list[str]:
    """A heatmap whose ramp saturates on a single feature is a dot map - and one
    in an encoding the target does not draw is not a map at all.

    Two assertions, and the second one exists because this check reported
    **4 of 4 green on a web map with an invisible layer**. That is the sharpest
    thing this folder has measured: every check here reads the stored item, and
    storage and rendering are different facts. The encoding rule below is the
    only way a read-back verifier can carry what only a screenshot could see.

    What was measured on ArcGIS Enterprise 12.1, one publish each:

    | Encoding | Stored | Drawn |
    |---|---|---|
    | `blurRadius`/`minPixelIntensity`/`maxPixelIntensity` (deprecated) | yes | yes, but only `blurRadius` has any effect |
    | `radius`/`minDensity`/`maxDensity` (current) | yes | **nothing at all** |

    So the target's constraint decides the representation, exactly as with
    `uniqueValueInfos` over `uniqueValueGroups` one layer up and `geo_point` in
    `opensearch` one repository over - except that here the newer form is not
    merely unsupported, it is silently empty. The verifier now refuses the
    encoding that draws nothing.

    The saturation assertion is the original one, and it needs a fact the web
    map does not contain: the largest value of the weighting field. A pixel's
    intensity is the sum of the kernel-weighted contributions of the points near
    it, so the peak intensity of an **isolated** point is exactly its own
    weight. Set the ceiling below that - it was a percentile of the weighting
    field itself, in EUR/sqm, which is not a unit of intensity at all - and
    every lone feature reaches the top of the ramp alone. Deliberately a ratio
    rather than a strict inequality: a ceiling merely equal to the maximum
    weight is just as saturated.
    """
    # The specification offers two encodings and a stored web map may carry
    # either, so the check reads both rather than assuming the one the builder
    # happens to write today: `blurRadius`/`minPixelIntensity`/
    # `maxPixelIntensity` is the deprecated Gaussian form, `radius`/
    # `minDensity`/`maxDensity` the current kernel-density one. Same rule as the
    # three `geo_point` encodings in `opensearch`: where a spec allows several,
    # decode all of them and let the assertion do the deciding.
    field = renderer.get("field")
    ceiling = renderer.get("maxPixelIntensity", renderer.get("maxDensity"))
    floor = renderer.get("minPixelIntensity", renderer.get("minDensity"))
    if field is None:
        return []  # an unweighted heatmap is pure density and has no such trap
    values = columns.get(field)
    if not values:
        return [f"the heatmap weights on {field!r}, which the source CSV does not carry"]
    if ceiling is None or floor is None:
        missing = "upper" if ceiling is None else "lower"
        return [
            f"the heatmap carries no {missing} intensity bound in either encoding "
            f"(maxPixelIntensity/minPixelIntensity or maxDensity/minDensity)"
        ]
    encoding = "density" if "maxDensity" in renderer else "gaussian"
    failures_encoding: list[str] = []
    if encoding != EXPECTED_HEATMAP_ENCODING:
        failures_encoding.append(
            f"the heatmap is written in the {encoding!r} encoding "
            f"(radius/minDensity/maxDensity). ArcGIS Enterprise 12.1 stores it and "
            f"draws nothing - measured, one publish, an empty layer with every other "
            f"check green. Rebuild with --heatmap-form {EXPECTED_HEATMAP_ENCODING}"
        )
    failures = list(failures_encoding)
    largest = max(values)
    if ceiling <= largest * HEATMAP_SATURATION_MARGIN:
        failures.append(
            f"maxPixelIntensity is {ceiling:,.2f} against a largest {field} of "
            f"{largest:,.2f}: a single isolated feature reaches "
            f"{min(1.0, (largest - floor) / (ceiling - floor)) if ceiling > floor else 1.0:.0%} "
            f"of the ramp on its own, so the heatmap saturates before any two features "
            f"overlap"
        )
    if floor >= ceiling:
        failures.append(
            f"minPixelIntensity {floor:,.2f} is not below maxPixelIntensity {ceiling:,.2f}"
        )
    return failures


def check_webmap(webmap_item, service_url: str | None, weights: dict[str, list[float]]) -> dict:
    """Five operational layers, four renderer types, one service.

    This is where a silently-dropped renderer becomes visible. Heatmap support
    on ArcGIS Enterprise **12.1 specifically** is UNVERIFIED - no
    version-pinned documentation page for it resolved - so the instance is
    asked rather than the document, which is the only way that claim can be
    settled.

    The `simple` layer gets a second assertion: a `simple` renderer whose
    `visualVariables` were dropped is still a perfectly valid `simple`
    renderer, drawing all 500 points at the same size. The layer would look
    finished and prove nothing.
    """
    data = webmap_item.get_data()
    if isinstance(data, str):
        data = json.loads(data)
    layers = data.get("operationalLayers") or []
    failures: list[str] = []
    rows = []
    types: list[str] = []
    urls = set()

    for layer in layers:
        renderer = (
            (layer.get("layerDefinition") or {}).get("drawingInfo") or {}
        ).get("renderer") or {}
        renderer_type = renderer.get("type")
        types.append(str(renderer_type))
        urls.add(layer.get("url"))
        variables = [v.get("type") for v in (renderer.get("visualVariables") or [])]
        rows.append(
            {
                "id": layer.get("id"),
                "title": layer.get("title"),
                "renderer": renderer_type,
                "field": renderer.get("field") or renderer.get("field1"),
                "visual_variables": variables,
                "url": layer.get("url"),
                "ramp": (
                    "{} .. {} ({} {}, referenceScale {})".format(
                        renderer.get("minPixelIntensity", renderer.get("minDensity")),
                        renderer.get("maxPixelIntensity", renderer.get("maxDensity")),
                        "blurRadius" if "blurRadius" in renderer else "radius",
                        renderer.get("blurRadius", renderer.get("radius")),
                        renderer.get("referenceScale", "absent"),
                    )
                    if renderer_type == "heatmap" else ""
                ),
            }
        )
        if renderer_type == "heatmap":
            failures.extend(check_heatmap_ramp(renderer, weights))
        if renderer_type == "simple" and EXPECTED_VISUAL_VARIABLE not in variables:
            failures.append(
                f"layer {layer.get('id')!r} is a simple renderer without a "
                f"{EXPECTED_VISUAL_VARIABLE} visual variable - it would draw every "
                f"feature at the same size and still look finished"
            )

    if len(layers) != EXPECTED_LAYER_COUNT:
        failures.append(
            f"the web map carries {len(layers)} operational layers, expected "
            f"{EXPECTED_LAYER_COUNT}"
        )
    seen = {name: types.count(name) for name in set(types)}
    if seen != EXPECTED_RENDERER_COUNTS:
        failures.append(
            f"renderer types are {seen}, expected {EXPECTED_RENDERER_COUNTS}. A "
            f"class-breaks layer that went missing leaves a map that still draws"
        )
    if len(urls) != 1:
        failures.append(
            f"the operational layers point at {len(urls)} distinct URLs: {sorted(urls)}. "
            f"The architecture of this use case is one service read five ways."
        )
    elif service_url and not (urls and next(iter(urls)).startswith(service_url)):
        failures.append(
            f"the operational layers point at {next(iter(urls))!r}, not at the feature "
            f"service that was published ({service_url!r})"
        )
    if "{{" in json.dumps(data):
        failures.append(
            "the stored web map still contains an unsubstituted placeholder. This item "
            "loads, draws its frame and shows no data."
        )
    if not (data.get("baseMap") or {}).get("baseMapLayers"):
        failures.append("the stored web map carries no baseMap block")
    # The committed artifact carries underscore-prefixed keys as notes to a
    # reader; the publisher strips them. Asserting their absence proves the
    # strip happened, and the failure is cheap to describe: a live web map
    # carrying this repository's commentary.
    notes = sorted(k for k in data if k.startswith("_"))
    if notes:
        failures.append(
            f"the stored web map still carries the documentation keys {notes} from "
            f"output/webmap.json - they should have been stripped before upload"
        )

    return {
        "name": "Five operational layers, four renderer types, one service",
        "passed": not failures,
        "failures": failures,
        "layers": rows,
        "basemap": (data.get("baseMap") or {}).get("title"),
        "version": data.get("version"),
        "largest_weight": next(
            (
                f"{max(weights[row['field']]):,.2f}"
                for row in rows
                if row.get("ramp") and row.get("field") in weights
            ),
            None,
        ),
    }


# ---------------------------------------------------------------------------
# Check 6 - the items
# ---------------------------------------------------------------------------


def check_items(gis, record: dict, expected_tag: str, expected_sharing: str) -> dict:
    """Do the items exist, with the right type, the tag, and the intended sharing?

    Sharing is checked rather than assumed because it is the one property of
    this run that is visible to other people. The default is private, and an
    item that ended up wider than intended is a finding, not a detail.
    """
    expected_types = {
        "csv": "CSV",
        "feature_layer": "Feature Service",
        "webmap": "Web Map",
    }
    failures: list[str] = []
    rows = []
    for key, entry in (record.get("items") or {}).items():
        item = gis.content.get(entry["id"])
        if item is None:
            failures.append(f"{key}: item {entry['id']} does not exist")
            rows.append({"key": key, "id": entry["id"], "exists": False})
            continue
        try:
            level = str(item.sharing.sharing_level)
        except Exception as exc:  # pragma: no cover - portal dependent
            level = f"<unreadable: {exc}>"
        row = {
            "key": key, "id": item.id, "exists": True, "type": item.type,
            "title": item.title, "tags": list(item.tags or []), "sharing": level,
        }
        rows.append(row)
        want_type = expected_types.get(key)
        if want_type and item.type != want_type:
            failures.append(f"{key}: item type is {item.type!r}, expected {want_type!r}")
        if expected_tag not in (item.tags or []):
            failures.append(f"{key}: item does not carry the tag {expected_tag!r}")
        if expected_sharing.upper() not in level.upper():
            failures.append(
                f"{key}: sharing level is {level!r}, expected {expected_sharing!r}"
            )
    for key in expected_types:
        if key not in (record.get("items") or {}):
            failures.append(f"the run record has no {key!r} item - was the stage run?")
    return {
        "name": "Items exist, typed, tagged, shared as intended",
        "passed": not failures,
        "failures": failures,
        "items": rows,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def render_report(results: list[dict], context: dict) -> str:
    passed = sum(1 for r in results if r["passed"])
    lines = [
        "# Portal verification report - Munster rent census",
        "",
        f"- Portal: `{context['portal_redacted']}`",
        f"- Verified: {context['when']}",
        f"- Feature service: `{context['service_url_redacted']}`",
        f"- Run record: `{context['run_record']}`",
        f"- Checks passed: **{passed} of {len(results)}**",
        "",
        "Generated by `scripts/verify_portal.py`. The host name is redacted: it is the",
        "endpoint of a real internal system, and CLAUDE.md section 11 keeps those out of a",
        "public repository. Checks 1 and 2 are the offline ones in",
        "[`verification_report_coordinates.md`](verification_report_coordinates.md);",
        "these are 3 to 6.",
        "",
        "Four checks is a decision, not a shortfall - see the README's *Verification*",
        "section and the four omissions recorded there.",
        "",
        "## Summary",
        "",
        "| # | Check | Result | Failures | Info |",
        "|---|---|---|---|---|",
    ]
    for number, result in enumerate(results, start=3):
        lines.append(
            f"| {number} | {result['name']} | "
            f"{'PASS' if result['passed'] else 'FAIL'} | {len(result['failures'])} | "
            f"{len(result.get('info') or [])} |"
        )
    lines.append("")

    for number, result in enumerate(results, start=3):
        lines += [f"## {number}. {result['name']}", ""]
        if result["failures"]:
            lines += [f"- **FAIL:** {f}" for f in result["failures"]] + [""]
        else:
            lines += ["_No failures._", ""]
        if result.get("info"):
            lines += [f"- **INFO:** {f}" for f in result["info"]]
            if result.get("retrofit_claim"):
                lines.append(
                    f"- **INFO:** the `updateDefinition` retrofit of those lengths "
                    f"{result['retrofit_claim']} - and the service still reports the "
                    f"lengths above. The confirmation is the finding."
                )
            lines += [
                "",
                "Reported rather than failed, and the demotion is itself a measurement:",
                "the platform sizes hosted string columns itself, the documented way to",
                "change them afterwards answers success and changes nothing, so there is",
                "no defect left on this side to fix. A check that can only ever be red",
                "carries no information. The **types** still fail this check, and that is",
                "the claim this use case makes.",
                "",
            ]

        if "rows" in result and result["name"].startswith("Field types"):
            lines += [
                "Three-way comparison: what this repository **declared**, what the portal",
                "**stored**, and what the portal **would have guessed** if nothing had been",
                "declared (`content.analyze`). The third column is the central measurement",
                "of this use case.",
                "",
                "| Field | Declared | Stored | Portal's guess |",
                "|---|---|---|---|",
            ]
            for row in result["rows"]:
                declared = row["declared"] + (
                    f" ({row['declared_length']})" if row["declared_length"] else ""
                )
                stored = (row["stored"] or "-") + (
                    f" ({row['stored_length']})" if row.get("stored_length") else ""
                )
                guess = row["portal_guess"] or "_not recorded_"
                marker = " **<-**" if row["portal_guess"] and row["portal_guess"] != row["declared"] else ""
                lines.append(f"| `{row['field']}` | {declared} | {stored} | {guess}{marker} |")
            lines += [
                "",
                f"The portal's guess differs from the declaration in "
                f"**{len(result['guess_disagreements'])}** of {len(result['rows'])} fields."
                if result["guess_available"]
                else "The portal's guess was not recorded - run the `publish` stage to "
                "capture `analyze_publish_parameters.json`.",
                "",
            ]

        if result["name"] == "Count and extent":
            extent = result.get("extent") or {}
            bounds = result.get("expected_bounds") or {}
            lines += [
                f"- Features: **{result.get('count')}** of "
                f"{result.get('expected_count')} expected",
                f"- Unit measured: **{result.get('unit')}** "
                f"(the layer reports WKID {result.get('wkid')})",
                "",
                "| Bound | Layer reports | Expected range |",
                "|---|---|---|",
            ]
            for key, low, high in (
                ("xmin", "expected_xmin", "expected_xmax"),
                ("xmax", "expected_xmin", "expected_xmax"),
                ("ymin", "expected_ymin", "expected_ymax"),
                ("ymax", "expected_ymin", "expected_ymax"),
            ):
                if key in extent and bounds:
                    lines.append(
                        f"| `{key}` | {float(extent[key]):,.2f} | "
                        f"{bounds[low]:,.2f} .. {bounds[high]:,.2f} |"
                    )
            lines += [
                "",
                "Both bounds are printed on purpose. `targetSR` was declared as WKID 102100,",
                "so this layer stores **metres** while its source CSV is degrees - and",
                "\"inside the box\" in the wrong unit is how a hundred points ended up within",
                "52 metres of 0 N 0 E in `egdb_import` without a single error anywhere.",
                "",
            ]

        if "layers" in result:
            lines += [
                "| Layer id | Title | Renderer | Field | Visual variables |",
                "|---|---|---|---|---|",
            ]
            for row in result["layers"]:
                lines.append(
                    f"| `{row['id']}` | {row['title']} | `{row['renderer']}` | "
                    f"`{row['field']}` | {', '.join(row['visual_variables']) or '-'} |"
                )
            lines += [
                "",
                f"- Basemap: {result.get('basemap')}",
                f"- Web Map Specification version stored: {result.get('version')}",
            ]
            for row in result["layers"]:
                if row.get("ramp"):
                    lines.append(
                        f"- Heatmap intensity ramp: {row['ramp']}, against a largest "
                        f"`{row['field']}` of {result.get('largest_weight', '?')}"
                    )
            lines += [
                "",
                "All five layers carry the same service URL - one copy of the data in the",
                "ArcGIS Data Store, read five ways. `classBreaks` appears twice on purpose:",
                "`rent_eur_sqm` is rendered both as a heatmap and as quantile classes, and",
                "the pair is the point. Heatmap support on Enterprise 12.1 was",
                "**UNVERIFIED** in the documentation, so this table is the answer.",
                "",
                "The heatmap ramp is asserted, not just reported. A pixel's intensity is",
                "the sum of the kernel-weighted contributions around it, so an isolated",
                "feature peaks at exactly its own weight: a `maxPixelIntensity` at or below",
                "the largest weight makes every lone feature reach the top colour by",
                "itself, and the map draws a dot map while looking like a density surface.",
                "",
            ]

        if "items" in result:
            lines += ["| Role | Type | Title | Sharing | Tagged |", "|---|---|---|---|---|"]
            for row in result["items"]:
                if not row.get("exists"):
                    lines.append(f"| {row['key']} | _missing_ | - | - | - |")
                    continue
                lines.append(
                    f"| {row['key']} | {row['type']} | {row['title']} | "
                    f"{row['sharing']} | {'yes' if context['tag'] in row['tags'] else 'no'} |"
                )
            lines += [
                "",
                "Item ids are deliberately absent from this committed report: they change on",
                "every run, and `output/` has to stay regenerable from `input/` plus the",
                "documented command. They live in the run record under `build/`.",
                "",
            ]

    return "\n".join(lines)


def redact_host(url: str | None) -> str:
    """Replace the host of a URL with a placeholder, keeping the path shape.

    The path is the informative part - `/server/rest/services/Hosted/<name>/
    FeatureServer` says what kind of service this is - and the host is the one
    part that must not be published.
    """
    if not url:
        return "-"
    try:
        scheme, rest = url.split("://", 1)
    except ValueError:
        return "<redacted>"
    host, _, path = rest.partition("/")
    return f"{scheme}://<portal-host>/{path}" if path else f"{scheme}://<portal-host>"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_portal.py",
        description=(
            "Verify what the portal stored: that the declared field types survived the "
            "publish, that the feature count and extent are right in the unit the layer "
            "actually stores, that the web map carries five operational layers with four "
            "renderer types on one service, and that every item is typed, tagged and "
            "shared as intended. Exit code 0 if all four pass."
        ),
        epilog=(
            "Example:\n"
            "  export PORTAL_PASSWORD=...\n"
            "  build/venv_api/bin/python scripts/verify_portal.py \\\n"
            "      --portal https://portal.example.com/portal --user devsummit \\\n"
            "      --run-record build/portal_run.json \\\n"
            "      --report output/verification_report_portal.md\n\n"
            "The report redacts the portal host. Item ids stay in the run record under\n"
            "build/, never in the committed report - they change on every run."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--portal", required=True, metavar="URL", help="portal URL")
    parser.add_argument("--user", required=True, metavar="NAME", help="portal user")
    parser.add_argument(
        "--password", default=None, metavar="SECRET",
        help=f"portal password; defaults to ${PASSWORD_ENV}. Never printed",
    )
    parser.add_argument(
        "--run-record", type=Path, default=Path("build/portal_run.json"), metavar="JSON",
        help="the run record written by publish_to_portal.py (default: %(default)s)",
    )
    parser.add_argument(
        "--declared", type=Path, default=Path("output/publish_parameters.json"),
        metavar="JSON",
        help="the declared publish parameters, read as data and never imported "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--guessed", type=Path, default=Path("output/analyze_publish_parameters.json"),
        metavar="JSON",
        help="the portal's own guessed publish parameters, captured during the publish "
        "stage (default: %(default)s)",
    )
    parser.add_argument(
        "--districts", type=Path, default=Path("input/muenster_districts.json"),
        metavar="JSON",
        help="districts fixture; its bounding_box is the expected extent, projected "
        "here into the unit the layer stores (default: %(default)s)",
    )
    parser.add_argument(
        "--expected-count", type=int, default=None, metavar="N",
        help="expected feature count; defaults to the row count of the CSV named by "
        "--csv",
    )
    parser.add_argument(
        "--csv", type=Path, default=Path("output/muenster_rent_census.csv"),
        metavar="CSV",
        help="the source CSV, used only to count rows (default: %(default)s)",
    )
    parser.add_argument(
        "--expected-sharing", default="PRIVATE", metavar="LEVEL",
        help="the sharing level every item should carry (default: %(default)s)",
    )
    parser.add_argument(
        "--report", type=Path, default=None, metavar="MD",
        help="write the Markdown report here. No default (CLAUDE.md section 4); "
        "without it the report goes to stdout",
    )
    parser.add_argument(
        "--ca-cert", default=None, metavar="PEM",
        help="CA bundle for a private certificate authority; sets REQUESTS_CA_BUNDLE "
        "before arcgis is imported",
    )
    parser.add_argument(
        "--no-verify-cert", action="store_true",
        help="disable TLS verification. A debugging aid, not a fix",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.run_record.is_file():
        print(
            f"error: run record not found: {args.run_record}. It is written by "
            f"publish_to_portal.py --run-record and holds the item ids this script "
            f"verifies.",
            file=sys.stderr,
        )
        return 1
    if not args.declared.is_file():
        print(f"error: declared parameters not found: {args.declared}", file=sys.stderr)
        return 1

    record = json.loads(args.run_record.read_text(encoding="utf-8"))
    declared = json.loads(args.declared.read_text(encoding="utf-8"))
    guessed = (
        json.loads(args.guessed.read_text(encoding="utf-8"))
        if args.guessed.is_file() else None
    )
    box = json.loads(args.districts.read_text(encoding="utf-8"))["bounding_box"]

    expected_count = args.expected_count
    if expected_count is None:
        if not args.csv.is_file():
            print(
                f"error: --expected-count not given and {args.csv} not found",
                file=sys.stderr,
            )
            return 1
        with args.csv.open(encoding="utf-8", newline="") as handle:
            expected_count = sum(1 for _ in handle) - 1

    # The heatmap check needs the weighting column itself, not just a row count.
    numeric_columns = read_numeric_columns(args.csv) if args.csv.is_file() else {}

    password = args.password or os.environ.get(PASSWORD_ENV)
    if not password:
        print(
            f"error: no password. Set ${PASSWORD_ENV} or pass --password.",
            file=sys.stderr,
        )
        return 1

    try:
        gis = connect(args, password)
        layer_entry = (record.get("items") or {}).get("feature_layer")
        webmap_entry = (record.get("items") or {}).get("webmap")
        if not layer_entry:
            raise VerifyError(
                "the run record holds no feature_layer item - run the publish stage first"
            )
        layer_item = gis.content.get(layer_entry["id"])
        if layer_item is None:
            raise VerifyError(f"feature layer item {layer_entry['id']} does not exist")
        layer = layer_item.layers[0]

        results = [
            check_field_types(
                layer, declared, guessed, record.get("field_length_update")
            ),
            check_count_and_extent(layer, expected_count, box),
        ]
        if webmap_entry:
            webmap_item = gis.content.get(webmap_entry["id"])
            if webmap_item is None:
                raise VerifyError(f"web map item {webmap_entry['id']} does not exist")
            results.append(check_webmap(webmap_item, layer_item.url, numeric_columns))
        else:
            results.append(
                {
                    "name": "Five operational layers, four renderer types, one service",
                    "passed": False,
                    "failures": ["the run record holds no webmap item - was the stage run?"],
                    "layers": [],
                }
            )
        results.append(
            check_items(gis, record, record.get("tag", "devsummit-portal-publish"),
                        args.expected_sharing)
        )
    except VerifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    context = {
        "portal_redacted": redact_host(args.portal),
        "service_url_redacted": redact_host(layer_item.url),
        "run_record": str(args.run_record),
        "when": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tag": record.get("tag", "devsummit-portal-publish"),
    }
    report = render_report(results, context)
    if args.report is None:
        print(report)
    else:
        args.report.write_text(report + "\n", encoding="utf-8")

    passed = sum(1 for r in results if r["passed"])
    print(f"checks passed: {passed}/{len(results)}")
    for number, result in enumerate(results, start=3):
        print(
            f"  {number}. {'PASS' if result['passed'] else 'FAIL'} - {result['name']}"
            + (f" ({len(result['failures'])} failure(s))" if result["failures"] else "")
            + (f" [{len(result['info'])} info]" if result.get("info") else "")
        )
    if args.report is not None:
        print(f"wrote {args.report}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
