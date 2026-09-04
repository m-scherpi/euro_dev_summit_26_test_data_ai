"""The three geo_point formats ArcGIS can read, and how to write them.

Moved out of `index_stations.py` unchanged when a second indexer appeared. It
is imported by the **indexers only**. The verifiers deliberately do not import
it: they decode `location` from a second, independent reading of the OpenSearch
field specification, because a checker that calls the function it is checking
only proves the code agrees with itself (CLAUDE.md section 4).

Why there are three and not four:

**The obvious format is the one that does not work.** Esri states it plainly:
"The geopoint format that uses an object with a latitude and longitude is not
supported with ArcGIS." That is `{"lat": ..., "lon": ...}` - the first form in
the OpenSearch documentation, the form an LLM writes unprompted, and the form
that indexes fine, answers geo queries fine, and leaves ArcGIS unable to open
the layer. It is not offered here at all.

**The remaining three disagree about axis order**, which is the whole reason
this is a parameter rather than a constant:

| format | value                        | order    |
|--------|------------------------------|----------|
| array  | `[longitude, latitude]`      | lon, lat |
| string | `"latitude,longitude"`       | lat, lon |
| wkt    | `POINT (longitude latitude)` | lon, lat |

Two of three put longitude first, and the odd one out is the one that reads
most like prose. Hard-coding either order without a check is how points end up
in the Indian Ocean, so the choice is a flag and the search engine referees the
result: a bounding box that must match everything, plus its transpose that must
match nothing.
"""

from __future__ import annotations

GEO_FORMATS = ("array", "string", "wkt")


def format_location(latitude: float, longitude: float, geo_format: str):
    """Build the geo_point value in one of the three ArcGIS-readable formats.

    The object form `{"lat": ..., "lon": ...}` is intentionally not offered:
    OpenSearch accepts it, ArcGIS does not.
    """
    if geo_format == "array":
        return [longitude, latitude]           # GeoJSON order: lon, lat
    if geo_format == "string":
        return f"{latitude},{longitude}"       # OpenSearch string order: lat, lon
    if geo_format == "wkt":
        return f"POINT ({longitude} {latitude})"
    raise ValueError(f"unknown geo format: {geo_format!r}")
