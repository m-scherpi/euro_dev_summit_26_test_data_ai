"""The agreements this use case's writers share - and nothing else.

CLAUDE.md section 4 draws the line this module sits on: **code that has to
agree should be shared; code that has to check must not be.** Getting that
backwards produces either a bug that passes both sides or a conflict at row 0,
and both have already happened in this repository - `egdb_import` aborted at
row 0 because the analyser and the loader held two different definitions of
"empty", while `csv_data` only caught a 490 m projection error because the
verifier wrote the formula a second, different way.

So this module holds exactly three kinds of thing:

* the **column list** of the CSV, in order;
* the **declared Esri field type** of every column, which is what
  `build_portal_items.py` writes into `publishParameters.layerInfo.fields` and
  what `publish_to_portal.py --dry-run` coerces every row against;
* the **seed default** and the **service name default**, so a command typed
  from either README section reproduces the same artifact.

Three importers: `generate_census.py`, `build_portal_items.py` and
`publish_to_portal.py`. Both verifiers deliberately import nothing from here.
`verify_census.py` re-derives the bounding box from `input/` and writes the
projection formula in its own second form; `verify_portal.py` reads
`output/publish_parameters.json` **as data** and compares it against what the
portal actually stored. If either one imported this file, it would be checking
a constant against itself.

There is no projection function in this module, on purpose. The generator's
`ln(tan(pi/4 + phi/2))` and the verifier's `atanh(sin phi)` are the same
function written twice so that agreement between them is evidence.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

# EPSG:3857 uses a sphere of the WGS 84 semi-major axis radius. Shared because
# it is a constant of the coordinate system rather than a step of the
# computation - the two projection implementations must agree about the radius
# and disagree about everything else.
EARTH_RADIUS_M = 6378137.0

# The CSV is EPSG:4326 decimal degrees; the hosted layer will store EPSG:3857
# metres, because `targetSR` defaults to WKID 102100 (see the README's
# "Coordinate reference systems"). Both codes are named everywhere they matter,
# and the column names follow the CRS as CLAUDE.md section 4 requires:
# latitude/longitude for the geographic pair, x_3857/y_3857 for the projected
# one, latitude before longitude, x before y.
SOURCE_WKID = 4326
TARGET_WKID = 102100  # the deprecated Esri code for the same sphere as 3857
TARGET_LATEST_WKID = 3857

# Decimal places for the stored geographic coordinates. Round FIRST, then
# project: at five decimals (~1.1 m) projecting the unrounded value would leave
# x_3857/y_3857 disagreeing with the latitude/longitude in the same row, and
# only an independent recomputation would ever notice.
COORD_DECIMALS = 5
METRE_DECIMALS = 4  # a tenth of a millimetre; see the libm note below

FIELDNAMES = [
    "id",
    "address",
    "district",
    "latitude",
    "longitude",
    "x_3857",
    "y_3857",
    "rent_eur_sqm",
    "living_area_sqm",
    "rooms",
    "median_age",
    "household_size",
    "building_type",
    "year_built",
]

# The declared schema of the hosted feature layer, column by column.
#
# `columnNames` is deliberately *not* sent to the portal; `layerInfo.fields`
# overrides it, and that is the hook that turns a guess into a declaration. The
# portal is asked what it *would* have guessed - `content.analyze()` - and the
# answer is committed next to this one, because the diff between the two is this
# use case's central measurement.
#
# Two rules from CLAUDE.md section 4 decide almost every line below:
#
# * **Never infer a decimal coordinate as Single.** `esriFieldTypeSingle` is a
#   32-bit float carrying about seven significant decimal digits. A latitude of
#   51.96253 needs seven and an EPSG:3857 metre value like 831034.5127 needs
#   ten. The rounding is silent and the result is a plausible coordinate in the
#   wrong place, so everything decimal is `esriFieldTypeDouble` - including
#   `rent_eur_sqm`, which would fit in a Single and is stored as a Double
#   anyway rather than leaving the reader to work out which decimals were
#   special.
# * **A TEXT field needs an explicit length**, and the measured maximum is a
#   floor rather than the answer. The lengths here are round numbers with
#   headroom over what the generator can produce, and `build_portal_items.py`
#   refuses to write a declaration the committed CSV already exceeds.
FIELD_TYPES: dict[str, dict[str, object]] = {
    "id":              {"type": "esriFieldTypeInteger", "alias": "ID"},
    "address":         {"type": "esriFieldTypeString", "length": 80, "alias": "Address"},
    "district":        {"type": "esriFieldTypeString", "length": 40, "alias": "District"},
    "latitude":        {"type": "esriFieldTypeDouble", "alias": "Latitude (EPSG:4326)"},
    "longitude":       {"type": "esriFieldTypeDouble", "alias": "Longitude (EPSG:4326)"},
    "x_3857":          {"type": "esriFieldTypeDouble", "alias": "X (EPSG:3857, m)"},
    "y_3857":          {"type": "esriFieldTypeDouble", "alias": "Y (EPSG:3857, m)"},
    "rent_eur_sqm":    {"type": "esriFieldTypeDouble", "alias": "Rent (EUR/sqm)"},
    "living_area_sqm": {"type": "esriFieldTypeDouble", "alias": "Living area (sqm)"},
    "rooms":           {"type": "esriFieldTypeInteger", "alias": "Rooms"},
    "median_age":      {"type": "esriFieldTypeDouble", "alias": "Median age (years)"},
    "household_size":  {"type": "esriFieldTypeDouble", "alias": "Household size"},
    "building_type":   {"type": "esriFieldTypeString", "length": 40, "alias": "Building type"},
    "year_built":      {"type": "esriFieldTypeInteger", "alias": "Year built"},
}

# The fields the CSV publish path consumes as geometry. They stay in the
# attribute table on purpose: `latitude`/`longitude` are what the offline
# verifier checks and what `verify_portal.py` reads back to prove no coordinate
# was silently rewritten, and dropping them would make the hosted layer's
# geometry unfalsifiable.
LATITUDE_FIELD = "latitude"
LONGITUDE_FIELD = "longitude"

# Defaults, so a command copied from any README section produces the same bytes.
DEFAULT_SEED = 20260904
DEFAULT_COUNT = 500
DEFAULT_SERVICE_NAME = "muenster_rent_census"

# The one tag every item of this use case carries, so `--recreate` can find its
# own items and only its own. A fixed string rather than a generated one: a
# demo that runs twice has to be able to clean up after the run before it.
ITEM_TAG = "devsummit-portal-publish"

# Operational layer ids in the web map, in drawing order (bottom to top), each
# paired with the renderer type it must carry. `verify_portal.py` does NOT
# import this - it re-states the expected set from a second reading of the Web
# Map Specification - but `build_portal_items.py` and a later dashboard both
# need to agree on the ids, because a dashboard binds its map widget to them.
OPERATIONAL_LAYER_IDS = (
    "rent_heatmap",
    "rent_breaks",
    "age_breaks",
    "building_type",
    "area_size",
)


def esri_type_of(column: str) -> str:
    """The declared Esri field type of one CSV column."""
    try:
        return str(FIELD_TYPES[column]["type"])
    except KeyError:  # pragma: no cover - a typo in a caller, not in data
        raise KeyError(
            f"{column!r} is not a declared column. The declaration in census.py is the "
            f"single source of truth for the schema; add it there rather than special-casing "
            f"it in a caller. Declared columns: {', '.join(FIELD_TYPES)}"
        ) from None


def text_length_of(column: str) -> int | None:
    """The declared TEXT length, or None for a non-TEXT column."""
    spec = FIELD_TYPES[column]
    length = spec.get("length")
    return int(length) if length is not None else None


# ---------------------------------------------------------------------------
# Placeholder tokens
# ---------------------------------------------------------------------------
#
# `build_portal_items.py` writes these into `output/webmap.json`, and
# `publish_to_portal.py` substitutes them. They are an agreement between those
# two scripts, which is why they live here.
#
# They exist because a portal item id does not exist until the item is created
# and changes on every run. Writing a real id into `output/` would break the
# rule that the folder is regenerable from `input/` plus the documented command,
# and it would churn a committed artifact on every demo. The substituted bodies
# go to `build/` instead.
#
# The tokens are load-bearing rather than cosmetic: an unsubstituted token
# yields a web map that **loads**, draws its frame, shows its legend and
# displays no data. So the publisher asserts that no `{{` survives before any
# `content.add` - CLAUDE.md section 4's rule about the loud error being the
# harmless one, applied to an item instead of a coordinate.
TOKEN_SERVICE_URL = "{{FEATURE_SERVICE_URL}}"
TOKEN_ITEM_ID = "{{FEATURE_LAYER_ITEM_ID}}"

# The marker every token shares, and the thing the publisher greps for. Any
# `{{...}}` left in a body is a failure, including one this module never
# declared - a typo in a template must not pass because it is not on a list.
TOKEN_MARKER = "{{"
