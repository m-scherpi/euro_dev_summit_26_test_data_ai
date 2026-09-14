#!/usr/bin/env python3
"""Build every portal payload for the Munster rent census - offline, stdlib only.

This is the hinge of the use case, and the reason it has one. The three JSON
documents written here *are* the deliverable that reaches ArcGIS Enterprise:
the publish parameters that decide the hosted layer's schema, the service-level
renderer, and the complete Web Map. `publish_to_portal.py` adds nothing to
them - it substitutes two placeholders, uploads and reports.

The split is the same one `egdb_import` drew between its schema contract and
its arcpy loader, and it holds better here: there, the artifact was a *plan* of
what the licensed half would do. Here it is the **payload**. Every decision
worth reviewing - which field is a Double, how many class breaks, which
renderer goes on which layer, what the popup shows - is reviewable and diffable
with no portal, no licence and no credentials in the room.

Two things this script is deliberate about:

**The schema is declared, not guessed.** `publishParameters.layerInfo.fields`
carries an explicit type for every column, and `columnNames` is omitted because
`layerInfo.fields` overrides it. The portal is perfectly willing to guess
instead - `publish_to_portal.py` asks it to, with `content.analyze()`, and
commits the answer next to this one. The diff between the two files is the
central measurement of this use case.

**The same service URL is referenced five times.** The web map's five
operational layers all point at layer 0 of one feature service and differ only
in `layerDefinition.drawingInfo`. That is supported by the Web Map
Specification and it is the whole architecture in one sentence: one copy of the
data, five ways of reading it - four renderer types, one of them used twice on
purpose.

Standard library only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from census import (  # noqa: E402  (needs the path above)
    DEFAULT_SERVICE_NAME,
    FIELD_TYPES,
    LATITUDE_FIELD,
    LONGITUDE_FIELD,
    OPERATIONAL_LAYER_IDS,
    SOURCE_WKID,
    TARGET_LATEST_WKID,
    TARGET_WKID,
    TOKEN_ITEM_ID,
    TOKEN_SERVICE_URL,
)

# The Web Map Specification version these bodies are written against. Named
# rather than omitted: a web map without a version is interpreted as whatever
# the reading client assumes, and "which spec was this written for" is the first
# question when a renderer silently does not draw.
# https://developers.arcgis.com/web-map-specification/
WEBMAP_VERSION = "2.27"

# Default `maxRecordCount` for the hosted layer. 2000 is the portal's own
# default and is stated explicitly anyway, because a value the service decides
# for itself is a value that can change between releases - and the number
# decides whether a client sees all 500 features or a page of them.
DEFAULT_MAX_RECORD_COUNT = 2000

# An Esri online raster basemap. Chosen over a vector basemap on purpose: a
# vector basemap is referenced through a portal item id, and an item id from
# ArcGIS Online is not guaranteed to resolve on an Enterprise portal that has
# never been told about it, while this URL is a plain service reference. It is
# a flag, so an instance with its own basemap gallery can point at that instead.
#
# The basemap is also the one part of this map that carries somebody else's
# attribution. CLAUDE.md section 3: never crop it out of a published
# screenshot, and record the notice as text in the README as well - an image can
# be re-exported, the obligation cannot.
DEFAULT_BASEMAP_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer"
)
DEFAULT_BASEMAP_TITLE = "Topographic"

# Number of class breaks for the median-age layer. Five is the readable maximum
# for a sequential legend and it matches the number of building types, which
# keeps the two legends the same height on screen.
DEFAULT_CLASS_COUNT = 5

# Sequential five-class blue ramp for the class breaks (light to dark), and the
# Okabe-Ito qualitative palette for the categorical layer. Both are chosen for
# colour-vision deficiency: a sequential ramp stays ordered when hue is lost,
# and Okabe-Ito is designed to stay distinguishable. A renderer an audience
# cannot read is a renderer that proves nothing on a projector.
CLASS_BREAK_COLORS = [
    [239, 243, 255, 200],
    [189, 215, 231, 210],
    [107, 174, 214, 220],
    [49, 130, 189, 230],
    [8, 81, 156, 240],
]
CATEGORY_COLORS = [
    [230, 159, 0, 220],    # orange
    [86, 180, 233, 220],   # sky blue
    [0, 158, 115, 220],    # bluish green
    [0, 114, 178, 220],    # blue
    [204, 121, 167, 220],  # reddish purple
]
CATEGORY_FALLBACK_COLOR = [140, 140, 140, 200]

# YlOrRd stops for the heatmap. The first stop is fully transparent so empty
# space stays empty instead of being tinted; without it a heatmap over a whole
# city reads as one warm rectangle.
#
# The ramp climbs gradually on purpose. Its first version jumped to alpha 140 at
# ratio 0.01 and to the second colour at 0.40, which meant a lone point reached
# the orange half of the ramp on its own - the ramp saturated before any two
# points had a chance to overlap, and a heatmap that saturates on single points
# is a dot map drawn expensively.
HEATMAP_COLOR_STOPS = [
    {"ratio": 0.00, "color": [255, 255, 178, 0]},
    {"ratio": 0.25, "color": [254, 217, 118, 120]},
    {"ratio": 0.50, "color": [254, 178, 76, 175]},
    {"ratio": 0.75, "color": [253, 141, 60, 215]},
    {"ratio": 1.00, "color": [227, 26, 28, 245]},
]

# The two encodings the Web Map Specification offers for a heatmap. See
# `heatmap_renderer` for what each writes and what was measured about them.
HEATMAP_FORMS = ("gaussian", "density")
DEFAULT_HEATMAP_FORM = "gaussian"

# Kernel width for the heatmap, in screen pixels, and the window width the
# calibration assumes. Both are inputs to a measurement rather than taste: see
# `heatmap_calibration`.
HEATMAP_BLUR_RADIUS_PX = 25
HEATMAP_REFERENCE_WIDTH_PX = 1280

# Sequential five-class YlOrRd ramp for the rent class breaks. Deliberately the
# same hue family as the heatmap, because the two layers show the same column
# and the point of having both is that they can be compared at a glance.
RENT_BREAK_COLORS = [
    [255, 255, 178, 210],
    [254, 217, 118, 215],
    [254, 178, 76, 225],
    [253, 141, 60, 235],
    [227, 26, 28, 245],
]

# Size range in points for the sizeInfo visual variable.
SIZE_MIN_PT = 5.0
SIZE_MAX_PT = 26.0

# Extent padding, as a fraction of the data's own span. Without it the corner
# features sit exactly on the frame edge and half their symbol is clipped.
EXTENT_PADDING = 0.06


class BuildError(Exception):
    """A payload this builder refuses to write."""


# ---------------------------------------------------------------------------
# Measuring the CSV
# ---------------------------------------------------------------------------


def measure(csv_path: Path) -> dict:
    """Read the CSV once and measure everything the renderers need.

    Every renderer threshold below is derived from the data rather than typed
    in: the class breaks are quantiles of the actual `median_age` column, the
    size ramp spans the actual `living_area_sqm` range, and the categorical
    legend lists the building types that actually occur, in descending
    frequency. A renderer with hard-coded breaks looks fine and quietly puts
    every feature in one class the first time the generator's seed changes.
    """
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not rows:
        raise BuildError(f"{csv_path} has a header and no rows")

    missing = [c for c in FIELD_TYPES if c not in fieldnames]
    extra = [c for c in fieldnames if c not in FIELD_TYPES]
    if missing or extra:
        raise BuildError(
            f"{csv_path} does not match the declaration in census.py. "
            f"missing: {missing or 'none'} | undeclared: {extra or 'none'}. "
            f"The declaration is the schema; fix it there, not here."
        )

    numeric: dict[str, list[float]] = {}
    text_max: dict[str, int] = {}
    for column, spec in FIELD_TYPES.items():
        if spec["type"] == "esriFieldTypeString":
            text_max[column] = max(len(row[column]) for row in rows)
        else:
            try:
                numeric[column] = [float(row[column]) for row in rows]
            except ValueError as exc:
                raise BuildError(
                    f"{csv_path}: column {column!r} is declared {spec['type']} and holds a "
                    f"value that is not a number ({exc})"
                ) from None

    # A declared TEXT length the data already exceeds is a defect, not a
    # difference of opinion: it fails hundreds of rows into the publish, on the
    # portal's side, with an error about a row rather than about the schema.
    # Same refusal as `egdb_import`'s schema contract, for the same reason.
    for column, longest in text_max.items():
        declared = int(FIELD_TYPES[column]["length"])  # type: ignore[arg-type]
        if longest > declared:
            raise BuildError(
                f"column {column!r} is declared TEXT({declared}) in census.py, but its "
                f"longest value in {csv_path} is {longest} characters. Raise the "
                f"declaration - the publish would fail on the portal's side, mid-insert."
            )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["building_type"]] = counts.get(row["building_type"], 0) + 1

    return {
        "path": str(csv_path),
        "count": len(rows),
        "numeric": numeric,
        "text_max": text_max,
        "building_type_counts": dict(
            sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        # The heatmap's two intensity bounds cannot be read off a column - they
        # are a property of the points' arrangement on screen. See
        # `heatmap_calibration`.
        "heatmap_calibration": heatmap_calibration(
            numeric["x_3857"], numeric["y_3857"], numeric["rent_eur_sqm"]
        ),
    }


def quantile(values: list[float], fraction: float) -> float:
    """Linear-interpolated quantile of an unsorted list."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------


def marker(color: list[int], size: float = 8.0, outline_alpha: int = 120) -> dict:
    """One `esriSMS` circle. Written out rather than imported from a helper so
    the JSON in `output/` can be read against the specification directly."""
    return {
        "type": "esriSMS",
        "style": "esriSMSCircle",
        "color": color,
        "size": size,
        "angle": 0,
        "xoffset": 0,
        "yoffset": 0,
        "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                    "color": [255, 255, 255, outline_alpha], "width": 0.5},
    }


# ---------------------------------------------------------------------------
# The four renderers
# ---------------------------------------------------------------------------


def _spearman(left: list[float], right: list[float]) -> float:
    """Rank correlation, written out because this module is stdlib-only.

    Ties are not averaged. The inputs here are sums of continuous kernel
    weights, where an exact tie does not occur; a column with repeated values
    would need the proper treatment.
    """
    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: values[index])
        out = [0.0] * len(values)
        for position, index in enumerate(order):
            out[index] = float(position)
        return out

    a, b = ranks(left), ranks(right)
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(
        sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b)
    )
    return numerator / denominator if denominator else 0.0


def heatmap_calibration(
    xs: list[float],
    ys: list[float],
    weights: list[float],
    blur_px: int = HEATMAP_BLUR_RADIUS_PX,
    reference_width_px: int = HEATMAP_REFERENCE_WIDTH_PX,
) -> dict:
    """Measure what pixel intensities this data actually produces.

    **`maxPixelIntensity` is not in the unit of the weighting field**, and the
    first version of this file assumed it was: it set the value to the 95th
    percentile of `rent_eur_sqm` (19.28 EUR/sqm) and produced a map on which
    every single point was a saturated red blob. A pixel's intensity is the sum
    of the kernel-weighted contributions of every point near it, so the two
    numbers share no unit and only happen to be the same order of magnitude.

    The arithmetic that makes it fatal is worth stating, because it is
    independent of zoom: the peak intensity of an **isolated** point is exactly
    its own weight. With a ceiling of 19.28 and rents up to 22.75, every lone
    dwelling reached 60-100 % of the ramp by itself, and no amount of
    overlapping could add anything visible on top. Whatever the heatmap was
    showing, it was not "where rents are high".

    So the ceiling is measured instead. A Gaussian kernel is evaluated over a
    pixel grid at a reference resolution derived from the map's own extent, and
    the ramp is anchored on percentiles of the occupied pixels: the floor at the
    75th so a lone point starts the ramp rather than finishing it, the ceiling
    at the 99th so the top colour means genuine overlap.

    Two honest limits, both recorded in the artifact rather than smoothed over:

    * **The kernel is an assumption.** Esri does not publish the shape of the
      blur, so this uses a Gaussian truncated at 3 sigma with
      `sigma = blurRadius / 3`. The calibration is therefore an approximation
      of the client's arithmetic, not a reproduction of it.
    * **Intensity is scale-dependent, and the deprecated renderer has no
      `referenceScale`.** These numbers hold for the map's initial extent; zoom
      in far enough and the same data spreads out and cools down. The current
      kernel-density form of the renderer has a `referenceScale` property for
      exactly this, and it is unavailable here for the reason recorded in
      `heatmap_renderer`.

    Every returned float is rounded. `exp` is a libm function and libm is not
    standardised to the last bit (CLAUDE.md section 10), so an unrounded value
    here would change the artifact's hash between platforms without changing
    anything about the map.
    """
    span_x = (max(xs) - min(xs)) * (1 + 2 * EXTENT_PADDING)
    resolution = span_x / reference_width_px
    sigma_px = blur_px / 3.0
    sigma_m = sigma_px * resolution
    cutoff_px = 3.0 * sigma_px

    x0, y0 = min(xs), min(ys)
    grid: dict[tuple[int, int], float] = {}
    for x, y, weight in zip(xs, ys, weights):
        cx, cy = (x - x0) / resolution, (y - y0) / resolution
        for i in range(math.floor(cx - cutoff_px), math.ceil(cx + cutoff_px) + 1):
            for j in range(math.floor(cy - cutoff_px), math.ceil(cy + cutoff_px) + 1):
                distance_sq = (i - cx) ** 2 + (j - cy) ** 2
                if distance_sq > cutoff_px ** 2:
                    continue
                grid[(i, j)] = grid.get((i, j), 0.0) + weight * math.exp(
                    -distance_sq / (2 * sigma_px * sigma_px)
                )

    occupied = sorted(grid.values())
    floor = quantile(occupied, 0.75)
    ceiling = quantile(occupied, 0.99)

    # How much of this heatmap is density and how much is rent? Measured at the
    # point positions rather than on the grid, because that is where the
    # question is asked. `weighted` is what the renderer draws, `density` is the
    # same sum with every weight set to 1, and `local_rent` is the
    # kernel-weighted mean rent in the neighbourhood - the quantity a viewer
    # believes they are looking at.
    cutoff_m = 3.0 * sigma_m
    weighted: list[float] = []
    density: list[float] = []
    for x, y in zip(xs, ys):
        acc_w = acc_d = 0.0
        for ox, oy, weight in zip(xs, ys, weights):
            distance_sq = (x - ox) ** 2 + (y - oy) ** 2
            if distance_sq > cutoff_m ** 2:
                continue
            kernel = math.exp(-distance_sq / (2 * sigma_m * sigma_m))
            acc_w += weight * kernel
            acc_d += kernel
        weighted.append(acc_w)
        density.append(acc_d)
    local_rent = [w / d for w, d in zip(weighted, density)]

    return {
        "blur_radius_px": blur_px,
        "reference_width_px": reference_width_px,
        "reference_resolution_m_per_px": round(resolution, 3),
        "kernel_sigma_m": round(sigma_m, 1),
        "max_weight": round(max(weights), 2),
        "occupied_pixels": len(occupied),
        "min_pixel_intensity": round(floor, 2),
        "max_pixel_intensity": round(ceiling, 2),
        "pixel_intensity_percentiles": {
            "p50": round(quantile(occupied, 0.50), 2),
            "p75": round(floor, 2),
            "p90": round(quantile(occupied, 0.90), 2),
            "p99": round(ceiling, 2),
            "max": round(occupied[-1], 2),
        },
        "spearman_heat_vs_density": round(_spearman(weighted, density), 3),
        "spearman_heat_vs_local_rent": round(_spearman(weighted, local_rent), 3),
        # The scale the numbers above are calibrated for, as a map scale
        # denominator: resolution [m/px] * 96 dpi / 0.0254 m per inch. The
        # renderer's `referenceScale` is the only property that can tell a
        # client to stop renormalising per zoom level, and without it the
        # calibration is a statement about one scale that the viewer is free to
        # ignore at every other.
        "reference_scale": round(resolution * 96 / 0.0254),
    }


def heatmap_renderer(
    calibration: dict,
    form: str = DEFAULT_HEATMAP_FORM,
    reference_scale: bool = True,
) -> dict:
    """Rent per square metre as a heatmap, weighted by the rent value.

    Both intensity bounds come from `heatmap_calibration`, which measures them
    rather than borrowing them from the weighting field's own unit - the mistake
    this renderer shipped with, and the reason every point drew as a saturated
    blob.

    **The specification offers two forms and they are not interchangeable, so
    this is a flag rather than a choice made here.** `gaussian` writes
    `blurRadius` / `minPixelIntensity` / `maxPixelIntensity`, each marked
    deprecated - *"Only used for heatmaps calculated with Gaussian blur"* -
    while `density` writes the current `radius` / `minDensity` / `maxDensity`.
    Both carry `referenceScale`, which belongs to neither half and is the only
    property that pins the calibration to a scale.

    What was measured on ArcGIS Enterprise 12.1, one publish each:

    | Encoding | Stored | Drawn |
    |---|---|---|
    | `gaussian` (deprecated) | yes | yes - but only `blurRadius` has any effect |
    | `density` (current) | yes | **nothing at all** |

    Both halves took a screenshot to establish. Raising `blurRadius` from 12 to
    25 visibly enlarged the blobs, so that property reaches the renderer, while
    replacing a ceiling of 19.28 with 38.82 and a floor of 0 with 9.02 changed
    nothing at the same extent and zoom - two captures taken deliberately at a
    matched view, since that is the only way the comparison means anything. Then
    the current encoding was published and the layer disappeared - with `verify_portal.py` reporting **4 of 4 green**, because
    every check it has reads the stored item and storage is not rendering.

    Which is a more useful reading of "deprecated" than the one this file
    started with: it does not mean "still works", it means "still accepted" -
    and on this version the *current* form is the one that is merely accepted.

    So `gaussian` is the default by measurement rather than by caution.
    `--heatmap-form density` is kept because it is the right choice on a target
    that draws it, and because it reproduces the finding in one command; the
    verifier refuses it for a 12.1 target.
    """
    if form not in HEATMAP_FORMS:
        raise BuildError(
            f"unknown --heatmap-form {form!r}; expected one of {', '.join(HEATMAP_FORMS)}"
        )
    renderer = {
        "type": "heatmap",
        "field": "rent_eur_sqm",
        "colorStops": HEATMAP_COLOR_STOPS,
    }
    if reference_scale:
        renderer["referenceScale"] = calibration["reference_scale"]
    if form == "gaussian":
        renderer.update(
            {
                "blurRadius": calibration["blur_radius_px"],
                "minPixelIntensity": calibration["min_pixel_intensity"],
                "maxPixelIntensity": calibration["max_pixel_intensity"],
            }
        )
    else:
        renderer.update(
            {
                "radius": calibration["blur_radius_px"],
                "minDensity": calibration["min_pixel_intensity"],
                "maxDensity": calibration["max_pixel_intensity"],
            }
        )
    return renderer


def class_breaks_renderer(
    values: list[float],
    field: str,
    class_count: int,
    colors: list[list[int]],
    unit_label: str,
    decimals: int = 1,
) -> dict:
    """One numeric column in equal-count classes.

    Parameterised over the column because the web map now carries two of these:
    `median_age`, which is a demographic attribute, and `rent_eur_sqm`, which is
    the question the map exists to answer. Sharing the function rather than
    copying it matters here for the reason CLAUDE.md gives about code that has
    to *agree* - both legends must classify the same way for the comparison
    between them to mean anything. (Code that has to *check* still must not be
    shared, which is why `verify_portal.py` imports none of this.)

    Two traps in `classBreaks`, both avoided here on purpose:

    * A `classBreakInfo` carries `classMaxValue` and **no** `classMinValue`.
      The breaks run contiguously upward from the renderer's own `minValue`,
      and adding a per-class minimum is how a legend ends up with gaps that
      swallow features silently.
    * The breaks are **quantiles**, so every class holds roughly the same
      number of features. Equal-interval breaks over a normal-ish distribution
      put almost everything in the middle two classes, which looks like a
      rendering bug and is arithmetic.

    Class counts are reported in the artifact so the equal-count claim is
    checkable rather than asserted. They are counted against the **rounded**
    break edges that the renderer actually carries, not against the unrounded
    quantiles, so the printed counts are what the client will draw.
    """
    lowest = math.floor(min(values))
    edges = [
        round(quantile(values, (index + 1) / class_count), decimals)
        for index in range(class_count)
    ]
    edges[-1] = math.ceil(max(values))

    infos = []
    lower = float(lowest)
    for index, upper in enumerate(edges):
        members = sum(1 for value in values if lower <= value <= upper) if index == 0 \
            else sum(1 for value in values if lower < value <= upper)
        infos.append(
            {
                "classMaxValue": upper,
                "label": f"{lower:g} - {upper:g} {unit_label}",
                "description": f"{members} of {len(values)} features",
                "symbol": marker(colors[index % len(colors)], 9.0),
            }
        )
        lower = upper

    return {
        "type": "classBreaks",
        "field": field,
        "minValue": lowest,
        "classificationMethod": "esriClassifyQuantile",
        "classBreakInfos": infos,
    }


def unique_value_renderer(counts: dict[str, int]) -> dict:
    """Building type as a categorical renderer.

    `uniqueValueInfos` rather than the newer `uniqueValueGroups`, and the
    specification's own words are the reason - it says of `uniqueValueInfos`:

        "Deprecated. Please see uniqueValueGroups."

    The older form is used anyway, deliberately, and the choice is recorded so
    it does not read as ignorance. The target here is ArcGIS Enterprise 12.1,
    not the current ArcGIS Online: `uniqueValueGroups` is the form a newer
    client writes, and a renderer a 12.1 map viewer does not understand does
    not fall back to the old shape - it draws the `defaultSymbol` for every
    feature, which looks like a working map with a broken legend. The
    deprecated form is understood by both. That is the same reasoning as
    `opensearch`'s `geo_point` finding, one layer up: the consumer's
    constraint decides the representation, not the spec's preference.

    `defaultSymbol` is kept even though every occurring value has an info of
    its own, because "every occurring value" is a statement about this seed.
    """
    infos = []
    for index, (value, occurrences) in enumerate(counts.items()):
        infos.append(
            {
                "value": value,
                "label": f"{value} ({occurrences})",
                "description": f"{occurrences} features",
                "symbol": marker(CATEGORY_COLORS[index % len(CATEGORY_COLORS)], 9.0),
            }
        )
    return {
        "type": "uniqueValue",
        "field1": "building_type",
        "fieldDelimiter": ",",
        "defaultLabel": "Other building type",
        "defaultSymbol": marker(CATEGORY_FALLBACK_COLOR, 7.0),
        "uniqueValueInfos": infos,
    }


def size_renderer(areas: list[float]) -> dict:
    """Living area as a graduated symbol - one `simple` renderer, one visual variable.

    Exactly one `sizeInfo` visual variable and nothing else, so this layer
    demonstrates one renderer type rather than two at once. `household_size`
    would have been the obvious second variable and it goes into the popup
    instead.

    `minDataValue`/`maxDataValue` come from the data. Omitting them lets the
    client pick, and a client that picks 0 as the minimum draws every symbol at
    nearly the same size - the ramp is present and invisible.
    """
    return {
        "type": "simple",
        "label": "Dwelling",
        "description": "Symbol size scales with living area",
        "symbol": marker([120, 120, 120, 200], 10.0),
        "visualVariables": [
            {
                "type": "sizeInfo",
                "field": "living_area_sqm",
                "valueUnit": "unknown",
                "minSize": SIZE_MIN_PT,
                "maxSize": SIZE_MAX_PT,
                "minDataValue": round(min(areas), 1),
                "maxDataValue": round(max(areas), 1),
            }
        ],
    }


# ---------------------------------------------------------------------------
# Publish parameters
# ---------------------------------------------------------------------------


def layer_info_fields() -> list[dict]:
    """The declared schema, as `layerInfo.fields` wants it."""
    fields = []
    for name, spec in FIELD_TYPES.items():
        field: dict[str, object] = {
            "name": name,
            "alias": spec["alias"],
            "type": spec["type"],
            "nullable": False,
            "editable": True,
        }
        if "length" in spec:
            field["length"] = spec["length"]
        fields.append(field)
    return fields


def build_publish_parameters(
    service_name: str, measurement: dict, max_record_count: int
) -> dict:
    """The `publishParameters` for publishing the CSV item as a hosted layer.

    Written against the REST *Publish Item* reference. The parts that matter,
    each for a reason:

    * `locationType: "coordinates"` with `latitudeFieldName`/`longitudeFieldName`
      - the CSV carries coordinates, not addresses, so nothing is geocoded and
      no geocoding service is needed. That also means no coordinate leaves the
      file.
    * `sourceSR` **and** `targetSR` stated explicitly. `targetSR` defaults to
      102100, so the hosted layer stores Web Mercator **metres** even though
      every coordinate in the CSV is a degree. Stating it makes the CRS change
      a decision instead of a surprise, and it is why `verify_portal.py` has to
      say which unit its extent check measured - CLAUDE.md section 4, the Gulf
      of Guinea failure.
    * `layerInfo.fields` with a type per column, and **no** `columnNames`.
      `layerInfo.fields` overrides `columnNames`, so sending both would leave a
      reader guessing which one won. This is the hook that turns a guess into a
      declaration.
    """
    return {
        "name": service_name,
        "description": (
            "Fictitious rent-price census for Munster, generated for the "
            "Euro DevSummit 2026 talk on generating test data with GenAI. "
            "Nothing in this layer is real data."
        ),
        "locationType": "coordinates",
        "latitudeFieldName": LATITUDE_FIELD,
        "longitudeFieldName": LONGITUDE_FIELD,
        "columnDelimiter": ",",
        "sourceSR": {"wkid": SOURCE_WKID},
        "targetSR": {"wkid": TARGET_WKID, "latestWkid": TARGET_LATEST_WKID},
        "maxRecordCount": max_record_count,
        "layerInfo": {
            "name": service_name,
            "geometryType": "esriGeometryPoint",
            "fields": layer_info_fields(),
        },
        "_note": {
            "columnNames_omitted": (
                "layerInfo.fields overrides columnNames, so sending both would leave a "
                "reader guessing which one the portal used. This is the declaration; the "
                "portal's own guess is committed next to it in "
                "analyze_publish_parameters.json, and the diff between the two files is "
                "the central measurement of this use case."
            ),
            "crs_change": (
                f"The CSV is EPSG:{SOURCE_WKID} decimal degrees. targetSR "
                f"{TARGET_WKID} (= EPSG:{TARGET_LATEST_WKID}) means the hosted layer "
                "stores metres. Any extent check against it must say which unit it "
                "measured."
            ),
            "measured": {
                "rows": measurement["count"],
                "longest_text_values": measurement["text_max"],
            },
        },
    }


# ---------------------------------------------------------------------------
# Layer definition (service level)
# ---------------------------------------------------------------------------


def build_layer_definition(measurement: dict, class_count: int) -> dict:
    """The one service-level renderer, plus the field bodies for reference.

    A hosted layer carries its own `drawingInfo`, and that is what a client
    opening the *layer* sees - a query layer, a Pro connection, someone pasting
    the service URL into a browser. Without this step they get whatever the
    portal suggested at publish time, which is a renderer nobody in this
    repository chose. It renders `rent_eur_sqm`: a client that opens the bare
    layer should meet the question the data set exists to answer.

    Three top-level keys, and the separation is deliberate.
    `update_definition` is the renderer and is always sent.
    `field_length_update` is a **measurement**, sent only with
    `--retrofit-field-lengths`: the portal stored the declared `TEXT(80)` and
    `TEXT(40)` columns as `TEXT(8000)`, accepting the declaration and
    discarding its lengths without a word. Esri's `updateDefinition` reference
    says only *"When updating field properties, note that not all of these
    properties may be updated"* and does not say which - so the instance gets
    asked. Whatever it answers is the finding; the run record keeps the raw
    response either way. `declared_fields` stays a reference copy that is never
    sent.
    """
    text_fields = [
        field for field in layer_info_fields() if "length" in field
    ]
    return {
        "_note": (
            "Only `update_definition` is POSTed by publish_to_portal.py --stage "
            "layerdef. `field_length_update` is POSTed by the same stage only with "
            "--retrofit-field-lengths, as an experiment whose result is recorded in "
            "the run record. `declared_fields` is a reference copy for review and is "
            "never sent."
        ),
        "update_definition": {
            "drawingInfo": {
                "renderer": class_breaks_renderer(
                    measurement["numeric"]["rent_eur_sqm"],
                    "rent_eur_sqm",
                    class_count,
                    RENT_BREAK_COLORS,
                    "EUR/sqm",
                ),
                "transparency": 0,
                "labelingInfo": None,
            }
        },
        "field_length_update": {"fields": text_fields},
        "declared_fields": layer_info_fields(),
    }


# ---------------------------------------------------------------------------
# Web map
# ---------------------------------------------------------------------------


def popup_info(title: str, visible: list[str]) -> dict:
    """One popup, listing the whole attribute table with the layer's own theme first.

    Every field appears, because a popup that hides a column is a popup that
    cannot be cross-checked against the committed CSV field by field - which is
    how the `opensearch` screenshot confirmed three separate findings at once.
    """
    field_infos = []
    ordered = visible + [c for c in FIELD_TYPES if c not in visible]
    for name in ordered:
        spec = FIELD_TYPES[name]
        info: dict[str, object] = {
            "fieldName": name,
            "label": spec["alias"],
            "isEditable": False,
            "visible": True,
        }
        if spec["type"] == "esriFieldTypeDouble":
            digits = 5 if name in ("latitude", "longitude") else (
                4 if name in ("x_3857", "y_3857") else 2
            )
            info["format"] = {"places": digits, "digitSeparator": True}
        elif spec["type"] == "esriFieldTypeInteger":
            info["format"] = {"places": 0, "digitSeparator": name != "year_built"}
        field_infos.append(info)
    return {
        "title": title,
        "fieldInfos": field_infos,
        "description": None,
        "showAttachments": False,
        "mediaInfos": [],
    }


def operational_layer(
    layer_id: str, title: str, renderer: dict, visible: bool, popup_fields: list[str]
) -> dict:
    """One operational layer, pointing at layer 0 of the one feature service.

    All five carry the same `url` and the same `itemId` and differ only in
    `layerDefinition.drawingInfo`. That is supported by the Web Map
    Specification, and it is the architecture: one copy of the data in the
    ArcGIS Data Store, five ways of reading it.

    `id` is set explicitly instead of being left to the client. Autogenerated
    ids are stable only for as long as nobody edits the map, and a dashboard
    binds its widgets to exactly these strings - the deferred stage of this use
    case is the reason they are readable.
    """
    return {
        "id": layer_id,
        "title": title,
        "layerType": "ArcGISFeatureLayer",
        "url": f"{TOKEN_SERVICE_URL}/0",
        "itemId": TOKEN_ITEM_ID,
        "visibility": visible,
        "opacity": 1,
        "mode": 1,
        "layerDefinition": {"drawingInfo": {"renderer": renderer, "transparency": 0}},
        "popupInfo": popup_info(f"{title}: {{address}}", popup_fields),
    }


def build_webmap(
    measurement: dict,
    class_count: int,
    basemap_url: str,
    basemap_title: str,
    heatmap_form: str = DEFAULT_HEATMAP_FORM,
    reference_scale: bool = True,
) -> dict:
    """The complete Web Map, with placeholders where the item ids go.

    Hand-built JSON, and that is not a workaround. The pinned client library
    has no Web Map class at all: `arcgis` 2.4.1.1 ships no `arcgis.map` module
    and `arcgis.mapping` no longer exports `WebMap`, so `content.add` with a
    `text` body is the only route. Re-measure it with the command in the
    README's *There is no Web Map class* section.

    The map's own extent is computed from the CSV's `x_3857`/`y_3857` columns,
    which is the one place those redundant columns earn their keep offline: the
    hosted layer will store metres, so the extent has to be metres, and the
    file already carries them - independently verified against the degrees by
    `verify_census.py`.
    """
    xs = measurement["numeric"]["x_3857"]
    ys = measurement["numeric"]["y_3857"]
    pad_x = (max(xs) - min(xs)) * EXTENT_PADDING
    pad_y = (max(ys) - min(ys)) * EXTENT_PADDING

    # The *item's* extent is a different number in a different unit from the
    # map's own viewpoint, and conflating them is a real trap: an ArcGIS item's
    # `extent` property is documented as decimal degrees (WGS84), while this
    # web map's spatial reference - and therefore its viewpoint - is EPSG:3857
    # metres. Handing metres to the item property produces an item whose
    # extent is nonsense and whose map draws correctly, so nothing complains.
    # Same species as the Gulf-of-Guinea failure in `egdb_import`, one level up.
    lats = measurement["numeric"]["latitude"]
    lons = measurement["numeric"]["longitude"]
    pad_lat = (max(lats) - min(lats)) * EXTENT_PADDING
    pad_lon = (max(lons) - min(lons)) * EXTENT_PADDING

    # Two layers on one column, both visible, the heatmap underneath. That is
    # the point of the pair rather than an accident of ordering: the heatmap
    # answers "where are there many expensive dwellings", the class breaks
    # answer "where is it expensive", and only one of those is the question
    # anybody asks. The measurement is in the build report - the heatmap's
    # intensity correlates about as strongly with plain point density as it
    # does with the local rent level, so a viewer cannot tell the two apart.
    layers = [
        operational_layer(
            OPERATIONAL_LAYER_IDS[0],
            "Rent per square metre (heatmap)",
            heatmap_renderer(
                measurement["heatmap_calibration"], heatmap_form, reference_scale
            ),
            True,
            ["rent_eur_sqm", "district", "building_type"],
        ),
        operational_layer(
            OPERATIONAL_LAYER_IDS[1],
            "Rent per square metre (class breaks)",
            class_breaks_renderer(
                measurement["numeric"]["rent_eur_sqm"],
                "rent_eur_sqm",
                class_count,
                RENT_BREAK_COLORS,
                "EUR/sqm",
            ),
            True,
            ["rent_eur_sqm", "district", "living_area_sqm"],
        ),
        operational_layer(
            OPERATIONAL_LAYER_IDS[2],
            "Median age (class breaks)",
            class_breaks_renderer(
                measurement["numeric"]["median_age"],
                "median_age",
                class_count,
                CLASS_BREAK_COLORS,
                "years",
            ),
            False,
            ["median_age", "district", "year_built"],
        ),
        operational_layer(
            OPERATIONAL_LAYER_IDS[3],
            "Building type (unique values)",
            unique_value_renderer(measurement["building_type_counts"]),
            False,
            ["building_type", "year_built", "district"],
        ),
        operational_layer(
            OPERATIONAL_LAYER_IDS[4],
            "Living area (graduated size)",
            size_renderer(measurement["numeric"]["living_area_sqm"]),
            False,
            ["living_area_sqm", "rooms", "household_size"],
        ),
    ]

    return {
        "operationalLayers": layers,
        "baseMap": {
            "title": basemap_title,
            "baseMapLayers": [
                {
                    "id": "basemap_0",
                    "title": basemap_title,
                    "layerType": "ArcGISTiledMapServiceLayer",
                    "url": basemap_url,
                    "visibility": True,
                    "opacity": 1,
                }
            ],
        },
        "spatialReference": {"wkid": TARGET_WKID, "latestWkid": TARGET_LATEST_WKID},
        "initialState": {
            "viewpoint": {
                "targetGeometry": {
                    "spatialReference": {"wkid": TARGET_WKID, "latestWkid": TARGET_LATEST_WKID},
                    "xmin": round(min(xs) - pad_x, 2),
                    "ymin": round(min(ys) - pad_y, 2),
                    "xmax": round(max(xs) + pad_x, 2),
                    "ymax": round(max(ys) + pad_y, 2),
                }
            }
        },
        "authoringApp": "portal_publish/scripts/build_portal_items.py",
        "authoringAppVersion": "1.0.0",
        "version": WEBMAP_VERSION,
        "_item": {
            "note": (
                "Not part of the web map. An ArcGIS item's `extent` property is "
                "documented as decimal degrees (WGS84), while this map's own viewpoint "
                "is EPSG:3857 metres - two numbers in two units for two different "
                "properties. publish_to_portal.py reads the degrees from here for the "
                "item and the metres from initialState for the map."
            ),
            "extent_4326": [
                [round(min(lons) - pad_lon, 5), round(min(lats) - pad_lat, 5)],
                [round(max(lons) + pad_lon, 5), round(max(lats) + pad_lat, 5)],
            ],
        },
        "_note": {
            "underscore_keys_are_not_uploaded": (
                "Every top-level key starting with an underscore is documentation for a "
                "reader of this file and is stripped before the body is handed to "
                "content.add. Otherwise this commentary would end up inside the live "
                "web map, where the portal would tolerate it and nobody would want it."
            ),
            "one_service_five_layers": (
                "All five operational layers carry the same url and itemId and differ "
                "only in layerDefinition.drawingInfo. One copy of the data, five "
                "renderers - that is the architecture of this use case. classBreaks "
                "appears twice on purpose: rent_eur_sqm and median_age are classified "
                "the same way, and the rent layer exists to be compared against the "
                "heatmap drawn from the very same column."
            ),
            "placeholders": (
                f"{TOKEN_SERVICE_URL} and {TOKEN_ITEM_ID} are substituted by "
                "publish_to_portal.py. A portal item id does not exist until the item is "
                "created and changes on every run, so it cannot be committed to output/. "
                "An unsubstituted token yields a web map that loads, draws its frame and "
                "shows no data, which is why the publisher asserts that no double-brace "
                "marker survives before uploading anything. That sentence cannot spell the "
                "marker out: the assertion greps the serialised payload as text, so a note "
                "quoting the token literally trips the check on its own documentation - "
                "which is how this note came to be worded this way."
            ),
            "hand_built": (
                "arcgis 2.4.1.1 has no arcgis.map module and arcgis.mapping no longer "
                "exports WebMap, so there is no Web Map class to build this with. "
                "content.add with a text body is the only route, not a workaround."
            ),
            "basemap_attribution": (
                "The basemap is somebody else's data and carries their attribution. Never "
                "crop the provider notice out of a published screenshot, and record it as "
                "text in the README as well (CLAUDE.md section 3)."
            ),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def write_json(path: Path, body: dict) -> int:
    """Write one artifact with an explicit newline, and return its size.

    `newline="\\n"` is not decoration. A committed artifact whose bytes are
    rewritten by a checkout with `core.autocrlf=true` has a different hash
    without having a different value, and the repository pins line endings in
    `.gitattributes` for that reason (CLAUDE.md section 10).
    """
    text = json.dumps(body, indent=2, ensure_ascii=True, sort_keys=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return len(text.encode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_portal_items.py",
        description=(
            "Build the three portal payloads for the Munster rent census: the publish "
            "parameters that declare the hosted layer's schema, the service-level "
            "renderer, and the complete Web Map with five operational layers on one "
            "feature service. Standard library only - no portal, no licence and no "
            "credentials are involved, so every decision is reviewable offline."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/build_portal_items.py \\\n"
            "      --input        output/muenster_rent_census.csv \\\n"
            "      --service-name muenster_rent_census \\\n"
            "      --output-dir   output/\n\n"
            "Writes publish_parameters.json, layer_definition.json and webmap.json.\n"
            "The web map carries {{FEATURE_SERVICE_URL}} and {{FEATURE_LAYER_ITEM_ID}}\n"
            "as placeholders; publish_to_portal.py substitutes them and refuses to\n"
            "upload anything while a '{{' survives."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path, default=Path("output/muenster_rent_census.csv"),
        metavar="CSV", help="the generated census CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--service-name", default=DEFAULT_SERVICE_NAME, metavar="NAME",
        help="name of the hosted feature service to publish (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None, metavar="DIR",
        help="directory to write the three JSON artifacts into. No default on purpose "
        "(CLAUDE.md section 4: no convenient defaults on destructive arguments)",
    )
    parser.add_argument(
        "--class-count", type=int, default=DEFAULT_CLASS_COUNT, metavar="N",
        help="number of quantile class breaks for both class-breaks renderers "
        "(rent and median age) (default: %(default)s)",
    )
    parser.add_argument(
        "--heatmap-form", choices=HEATMAP_FORMS, default=DEFAULT_HEATMAP_FORM,
        help="which of the specification's two heatmap encodings to write: "
        "'gaussian' (blurRadius/minPixelIntensity/maxPixelIntensity, deprecated) or "
        "'density' (radius/minDensity/maxDensity, current). Measured on Enterprise "
        "12.1: gaussian draws, density stores and draws nothing at all "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--no-reference-scale", action="store_true",
        help="omit referenceScale from the heatmap. It pins the calibration to the "
        "scale it was computed for, and it has not yet been published together with "
        "the gaussian encoding - this flag isolates it if that layer stops drawing",
    )
    parser.add_argument(
        "--max-record-count", type=int, default=DEFAULT_MAX_RECORD_COUNT, metavar="N",
        help="maxRecordCount declared for the hosted layer (default: %(default)s)",
    )
    parser.add_argument(
        "--basemap-url", default=DEFAULT_BASEMAP_URL, metavar="URL",
        help="basemap service URL for the web map's baseMap block "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--basemap-title", default=DEFAULT_BASEMAP_TITLE, metavar="TEXT",
        help="title of the basemap layer (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.output_dir is None:
        print(
            "error: --output-dir is required. It has no default so that rebuilding the "
            "payloads for one service can never overwrite the artifacts of another.",
            file=sys.stderr,
        )
        return 1
    if not args.input.is_file():
        print(f"error: CSV not found: {args.input}", file=sys.stderr)
        return 1
    if not args.output_dir.is_dir():
        print(f"error: --output-dir is not a directory: {args.output_dir}", file=sys.stderr)
        return 1
    if args.class_count < 2:
        print("error: --class-count must be at least 2", file=sys.stderr)
        return 1

    try:
        measurement = measure(args.input)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    publish_parameters = build_publish_parameters(
        args.service_name, measurement, args.max_record_count
    )
    layer_definition = build_layer_definition(measurement, args.class_count)
    webmap = build_webmap(
        measurement, args.class_count, args.basemap_url, args.basemap_title,
        args.heatmap_form, not args.no_reference_scale,
    )

    artifacts = {
        "publish_parameters.json": publish_parameters,
        "layer_definition.json": layer_definition,
        "webmap.json": webmap,
    }
    for name, body in artifacts.items():
        size = write_json(args.output_dir / name, body)
        print(f"wrote {args.output_dir / name} | {size:,} bytes")

    rents = measurement["numeric"]["rent_eur_sqm"]
    ages = measurement["numeric"]["median_age"]
    areas = measurement["numeric"]["living_area_sqm"]
    print(
        f"measured {measurement['count']:,} rows | "
        f"rent {min(rents):.2f}..{max(rents):.2f} EUR/sqm | "
        f"age {min(ages):.1f}..{max(ages):.1f} | "
        f"area {min(areas):.1f}..{max(areas):.1f} sqm"
    )
    calibration = measurement["heatmap_calibration"]
    print(
        f"heatmap form: {args.heatmap_form} | referenceScale "
        + ("omitted" if args.no_reference_scale
           else f"1:{calibration['reference_scale']:,}")
        + " | measured on Enterprise 12.1: gaussian draws, density stores and draws "
        "nothing"
    )
    print(
        "heatmap calibration: "
        f"blurRadius {calibration['blur_radius_px']} px at "
        f"{calibration['reference_resolution_m_per_px']:.2f} m/px "
        f"(sigma {calibration['kernel_sigma_m']:.0f} m) | "
        f"minPixelIntensity {calibration['min_pixel_intensity']:.2f} (p75), "
        f"maxPixelIntensity {calibration['max_pixel_intensity']:.2f} (p99) | "
        f"a lone point peaks at its own weight, {calibration['max_weight']:.2f}"
    )
    print(
        "heatmap is density as much as value: rank correlation with plain point "
        f"density {calibration['spearman_heat_vs_density']:.3f}, with the local rent "
        f"level {calibration['spearman_heat_vs_local_rent']:.3f} - which is why the "
        "class-breaks layer on the same column exists"
    )
    for role, renderer in (
        ("service-level", layer_definition["update_definition"]["drawingInfo"]["renderer"]),
    ):
        print(
            f"class breaks ({role}, quantile, {renderer['field']}): "
            + ", ".join(
                f"<={info['classMaxValue']:g} ({info['description'].split(' of ')[0]})"
                for info in renderer["classBreakInfos"]
            )
        )
    print(
        "building types: "
        + ", ".join(f"{k}={v}" for k, v in measurement["building_type_counts"].items())
    )
    print(
        "renderers: "
        + ", ".join(
            f"{layer['id']}={layer['layerDefinition']['drawingInfo']['renderer']['type']}"
            for layer in webmap["operationalLayers"]
        )
    )
    print(
        "declared TEXT lengths vs longest value: "
        + ", ".join(
            f"{c}={measurement['text_max'][c]}/{FIELD_TYPES[c]['length']}"
            for c in measurement["text_max"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
