"""Verifier-side building blocks: what the geodatabase should say, and how to ask.

Imported by `verify_featureclass.py` **only**. Nothing in the importing half of
this use case may import it, and that is the invariant worth protecting: the
arcpy field-type names below are transcribed from Esri's field-type
documentation rather than derived from `schema.py`, so the two agreeing is
evidence instead of a tautology. CLAUDE.md section 4 - a checker that shares an
implementation with the thing it checks shares its bugs.

`schema.py` emits arcpy *tool keywords* (`SHORT`, `LONG`, `TEXT`); arcpy's
`Field.type` property reports *geodatabase type names* (`SmallInteger`,
`Integer`, `String`). They are two different vocabularies for the same set of
types, which is what makes the comparison meaningful: a mistranscription here
shows up as a failed check rather than as agreement.
"""

from __future__ import annotations

# arcpy Field.type -> the tool keyword AddField takes. Transcribed from
# https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm
# and the Add Field tool reference, not from schema.py.
KEYWORD_OF_FIELD_TYPE = {
    "SmallInteger": "SHORT",
    "Integer": "LONG",
    "BigInteger": "BIGINTEGER",
    "Single": "FLOAT",
    "Double": "DOUBLE",
    "String": "TEXT",
    "Date": "DATE",
    "DateOnly": "DATEONLY",
    "TimeOnly": "TIMEONLY",
    "TimestampOffset": "TIMESTAMPOFFSET",
    "Guid": "GUID",
    "GlobalID": "GLOBALID",
    "Blob": "BLOB",
    "Raster": "RASTER",
    "OID": "OID",
    "Geometry": "GEOMETRY",
}

# Columns the geodatabase adds and manages on its own. A feature class created
# by CreateFeatureclass has exactly these beyond the declared fields, and
# anything else is either a leftover from an earlier run or a field somebody
# added by hand - both worth failing on.
GEODATABASE_OWNED_TYPES = frozenset({"OID", "Geometry"})


class Check:
    """One verification result, rendered as a row of the report table."""

    def __init__(self, name: str, passed: bool | None, detail: str) -> None:
        self.name = name
        self.passed = passed  # None = informational
        self.detail = detail

    @property
    def verdict(self) -> str:
        if self.passed is None:
            return "INFO"
        return "PASS" if self.passed else "**FAIL**"


def render_check_table(checks: list[Check]) -> list[str]:
    """Render the checks as the report's summary table."""
    lines = ["| Check | Result | Detail |", "|---|---|---|"]
    for check in checks:
        lines.append(f"| {check.name} | {check.verdict} | {check.detail} |")
    return lines


def inside(x: float, y: float, box: dict[str, float]) -> bool:
    """Is the point inside the closed box?"""
    return box["x_min"] <= x <= box["x_max"] and box["y_min"] <= y <= box["y_max"]


def transpose(box: dict[str, float]) -> dict[str, float] | None:
    """Swap the axes of a box, or None if the result is not a valid box.

    Returns None when the transposed box would be degenerate or - for a
    geographic box - would demand latitudes outside -90..90. That case is a
    result, not an error: CLAUDE.md section 4 records that for five of seven
    airport regions the transposed box *does not exist*, because asking for
    Alaska's longitudes as latitudes is rejected outright. A check that cannot
    be posed must be reported as such rather than quietly counted as a pass.
    """
    swapped = {
        "x_min": box["y_min"],
        "x_max": box["y_max"],
        "y_min": box["x_min"],
        "y_max": box["x_max"],
    }
    if swapped["x_min"] >= swapped["x_max"] or swapped["y_min"] >= swapped["y_max"]:
        return None
    return swapped
