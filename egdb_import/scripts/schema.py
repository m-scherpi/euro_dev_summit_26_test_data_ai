"""The schema contract: measuring a source file's structure, in geodatabase terms.

This module is the hinge of the use case. It is imported by
`analyze_source.py`, which measures a CSV or JSON and writes the contract, and
by `import_to_egdb.py`, which reads the contract and builds the feature class
from it. It is deliberately **not** imported by `verify_featureclass.py`: the
verifier re-reads the field types out of the geodatabase and compares them
against the contract *as data*, so it must not share the code that produced
them (CLAUDE.md section 4 - a checker that shares an implementation with the
thing it checks shares its bugs).

Three things here are not obvious, and each one is a rule the geodatabase
imposes rather than a preference:

1. **An Enterprise Geodatabase has no boolean type.** ArcGIS field types are
   SHORT, LONG, FLOAT, DOUBLE, TEXT, DATE, GUID, GLOBALID, BLOB - and that is
   the whole list. A `true`/`false` column therefore has to become something
   else, and the honest something else is SHORT with 0/1. The substitution is
   recorded in the contract as `boolean_as_short` rather than applied silently,
   because a reader of the resulting attribute table sees a number and has no
   way to know it was ever a boolean.
   https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm

2. **The geodatabase's name limits are tighter than PostgreSQL's, and ArcGIS
   never quotes an identifier.** A field name may be 31 characters, not
   PostgreSQL's 63. And Esri is explicit: "ArcGIS does not delimit object
   names. Do not create any tables, feature classes, indexes, databases, users,
   roles, or other object names that require delimiters if you will be using
   them with ArcGIS." So a name that merely *needs* quoting - mixed case, a
   space, a reserved word - is a name ArcGIS cannot see, even though
   PostgreSQL stores it happily. Sanitising is therefore not cosmetic.
   https://desktop.arcgis.com/en/arcmap/10.7/manage-data/gdbs-in-postgresql/enterprise-geodatabase-limits.htm

3. **Never infer a decimal as FLOAT.** A 32-bit float carries about 7
   significant decimal digits; a latitude of 51.51264 needs 7 and an EPSG:3857
   metre value like 831034.51 needs 8. FLOAT would round the coordinate and the
   result would look entirely plausible. Every decimal becomes DOUBLE.

Type inference scans **every** row, not the first one. A column that is integer
for 99 rows and decimal on the hundredth is a decimal column, and the failure
mode of sampling is a truncated value rather than an error.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Geodatabase limits and vocabulary
# ---------------------------------------------------------------------------

# Enterprise geodatabase name limits, in ANSI characters. The field limit is
# the one that bites: PostgreSQL itself allows 63, so a name between 32 and 63
# characters is accepted by the database and unusable through ArcGIS.
MAX_FIELD_NAME_LEN = 31
MAX_TABLE_NAME_LEN = 128

# Column names the geodatabase manages itself. A source column landing on one
# of these is an error rather than something to rename around, because the
# collision means the source already carries an identity column and the caller
# has to decide what it is for. CLAUDE.md section 4: an identifier column is
# not an identifier - `objectid` and `ESRI_OID` in the airports export were
# both 1..N, both unique, and equal in zero rows.
GEODATABASE_MANAGED = frozenset({"objectid", "shape", "globalid", "se_anno_cad_data"})

# Curated from PostgreSQL's SQL key words appendix - the reserved words that
# plausibly occur as a column name in real data. Not the full list: the point is
# to catch `order`, `user` and `date`, not to reproduce the grammar.
# https://www.postgresql.org/docs/current/sql-keywords-appendix.html
SQL_RESERVED = frozenset(
    """
    all and any array as asc between both case cast check column constraint
    create current_date current_time current_timestamp current_user default
    desc distinct do else end except exists false for foreign from grant group
    having in initially inner intersect into is join leading left like limit
    localtime localtimestamp not null offset on only or order outer overlaps
    primary references returning right select session_user some symmetric table
    then to trailing true union unique user using values when where window with
    date time timestamp interval zone insert update delete set level
    """.split()
)

# The complete set of ArcGIS field types this importer emits. GUID, GLOBALID
# and BLOB exist but are never inferred: a GUID-shaped string stays TEXT unless
# somebody edits the contract, because guessing it would make the geodatabase
# manage a column the source owns.
ESRI_TYPES = ("SHORT", "LONG", "FLOAT", "DOUBLE", "TEXT", "DATE")

# TEXT is the only inferred type that needs a length, and the measured maximum
# is a floor rather than the answer: the next batch of data is longer. The
# factor is a documented default and a CLI flag, not a constant, because "1.5x
# the longest value seen" is a judgement call and should be visible as one.
DEFAULT_TEXT_HEADROOM = 1.5
TEXT_LENGTH_STEP = 10  # round the padded length up to a readable number
MIN_TEXT_LENGTH = 10


# Esri JSON field types, as an Esri REST FeatureSet declares them, mapped to the
# tool keyword AddField takes. A FeatureSet exported from a geodatabase carries
# its *own* schema in a `fields` block - real types and real TEXT lengths - and
# that is strictly better information than inference. It is not, however, taken
# on trust: `declared_field` below records the measurement beside the
# declaration and refuses the one case where they genuinely conflict.
# https://developers.arcgis.com/documentation/common-data-types/field.htm
ESRI_FIELD_TYPE_KEYWORD = {
    "esriFieldTypeSmallInteger": "SHORT",
    "esriFieldTypeInteger": "LONG",
    "esriFieldTypeSingle": "FLOAT",
    "esriFieldTypeDouble": "DOUBLE",
    "esriFieldTypeString": "TEXT",
    "esriFieldTypeDate": "DATE",
    "esriFieldTypeGUID": "GUID",
    "esriFieldTypeOID": "LONG",
    "esriFieldTypeGlobalID": "TEXT",
    "esriFieldTypeBlob": "BLOB",
}

# Declared types that cannot be carried over as they stand. An OID or a GlobalID
# in a source export is a value some *other* geodatabase assigned; recreating it
# as the same type here would hand our geodatabase a column it wants to manage
# itself. They become a plain LONG and a plain TEXT, and the substitution is
# recorded - CLAUDE.md section 4, an identifier column is not an identifier.
ESRI_MANAGED_SOURCE_TYPES = {
    "esriFieldTypeOID": (
        "The source declares this as its object id. Carried as a plain LONG, because the "
        "object id of this feature class is assigned by this geodatabase and the two are "
        "unrelated - they will agree only for as long as nothing is ever deleted."
    ),
    "esriFieldTypeGlobalID": (
        "The source declares this as a GlobalID. Carried as plain TEXT, because a GLOBALID "
        "column is system-managed and would be populated with new values rather than the "
        "source's."
    ),
}

GLOBALID_TEXT_LENGTH = 38  # "{" + 36 characters + "}"


class SchemaError(Exception):
    """A source the importer refuses to guess about."""


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

_NON_IDENTIFIER = re.compile(r"[^a-z0-9_]+")
_LEADING_JUNK = re.compile(r"^[^a-z]+")


def sanitize_name(raw: str, taken: Iterable[str] = (), limit: int = MAX_FIELD_NAME_LEN) -> str:
    """Turn a source column name into one ArcGIS can address without quoting.

    Lowercase first, because PostgreSQL folds unquoted identifiers to lowercase
    anyway - a column created as `Latitude` is `latitude` in the catalogue, and
    a tool that remembers the capital and ArcGIS that does not are two tools
    looking for different columns.

    Raises rather than renames on a collision with a geodatabase-managed name:
    a source column called `objectid` means the source has its own identity
    column, and silently calling it `objectid_1` next to the geodatabase's own
    `objectid` produces exactly the two-columns-that-look-like-an-object-id
    situation CLAUDE.md warns about.
    """
    name = _NON_IDENTIFIER.sub("_", raw.strip().lower())
    name = _LEADING_JUNK.sub("", name).strip("_")
    if not name:
        raise SchemaError(f"column name {raw!r} contains no usable characters")

    if name in GEODATABASE_MANAGED:
        raise SchemaError(
            f"column {raw!r} sanitises to {name!r}, which the geodatabase manages itself. "
            f"Pass --rename {raw}=source_{name} - a source object id belongs in a prefixed "
            "column so the attribute table stops inviting a join on it (CLAUDE.md section 4). "
            "The rename happens here rather than in the source, because input/ is read-only."
        )
    if name in SQL_RESERVED:
        name = f"{name}_"

    name = name[:limit]
    taken_set = {t.lower() for t in taken}
    if name not in taken_set:
        return name

    # Collision after truncation. Suffix with a counter, shortening the stem so
    # the result still fits - a name over the limit is invisible to ArcGIS, so
    # the limit wins over keeping the original prefix intact.
    for counter in range(1, 1000):
        suffix = f"_{counter}"
        candidate = f"{name[: limit - len(suffix)]}{suffix}"
        if candidate not in taken_set:
            return candidate
    raise SchemaError(f"cannot find a free name for {raw!r} within {limit} characters")


# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------

_TRUE = {"true", "t", "yes", "y"}
_FALSE = {"false", "f", "no", "n"}
_INT = re.compile(r"^[+-]?\d+$")
_DECIMAL = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")

# ISO 8601 date / datetime, the only date shape accepted without being told.
# A locale-dependent form like 03/04/2026 is ambiguous by construction - it is
# either 3 April or March 4 - so it stays TEXT rather than becoming a DATE that
# is wrong for half the year.
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")


def is_absent(value: Any) -> bool:
    """Absent, as opposed to blank-looking.

    A single space is **not** empty. CLAUDE.md section 4: a geodatabase's
    "empty" may be `" "` rather than NULL - measured at 825 of 880 rows of one
    column in the airports export, and 1,343 values across three columns. In a
    GIS client the cell looks empty and is not, so a filter on empty finds
    nothing and `IS NULL` finds nothing either.

    Treating it as empty here would have inserted NULL, which is a silent edit
    to somebody else's data. The space is what the source stores, so the space
    is what gets written; it is counted in the evidence instead of being tidied
    away.

    **Public, and imported by `import_to_egdb.py` on purpose.** The analyser
    decides a field's nullability with this predicate and the loader has to
    write exactly what was measured, so the two must agree - this is the same
    case as the shared readers in `sources.py`, and the opposite of the
    projection formulas that are deliberately written twice. When the loader
    had its own copy, the first run of the airports fixture aborted at row 0
    with "field 'field' is empty but the contract declares it non-nullable" -
    two definitions of empty, one file.
    """
    return value is None or (isinstance(value, str) and value == "")


@dataclass
class FieldSpec:
    """One column, as the geodatabase will hold it, plus why."""

    name: str
    source: str
    type: str
    length: int | None = None
    nullable: bool = True
    evidence: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "source": self.source, "type": self.type}
        if self.length is not None:
            out["length"] = self.length
        out["nullable"] = self.nullable
        out["evidence"] = self.evidence
        return out


def text_length_for(max_len: int, headroom: float) -> int:
    """Padded TEXT length: measured maximum, times headroom, rounded up."""
    padded = max(MIN_TEXT_LENGTH, math.ceil(max_len * headroom))
    return int(math.ceil(padded / TEXT_LENGTH_STEP) * TEXT_LENGTH_STEP)


def infer_field(
    source_name: str, values: list[Any], *, headroom: float = DEFAULT_TEXT_HEADROOM
) -> tuple[str, int | None, dict[str, Any]]:
    """Decide the Esri type for one column from all of its values.

    Returns `(type, length, evidence)`. The evidence dictionary is the reason
    the type was chosen, and it goes into the contract verbatim so that a
    reviewer can disagree with the inference without re-reading the data.
    """
    total = len(values)
    present = [v for v in values if not is_absent(v)]
    nulls = total - len(present)
    as_text = [v if isinstance(v, str) else str(v) for v in present]

    evidence: dict[str, Any] = {
        "rows": total,
        "nulls": nulls,
        "distinct": len(set(as_text)),
        "sample": as_text[:3],
    }

    # An all-empty column carries no evidence of a type at all. TEXT is the only
    # honest answer, and saying so beats picking a number type that happens to
    # accept nothing.
    if not present:
        evidence["reason"] = "no non-empty value in any row; type cannot be measured"
        return "TEXT", MIN_TEXT_LENGTH, evidence

    # Count the blank-but-not-empty values so they show up in the contract
    # instead of being discovered in an ArcGIS attribute table. They are carried
    # through verbatim; see `is_absent`.
    blank_but_not_empty = sum(1 for v in as_text if v != "" and v.strip() == "")
    if blank_but_not_empty:
        evidence["whitespace_only_values"] = blank_but_not_empty

    lowered = {v.strip().lower() for v in as_text}

    if lowered <= (_TRUE | _FALSE):
        evidence["reason"] = "every value is a boolean literal"
        evidence["boolean_as_short"] = True
        evidence["true_values"] = sorted(lowered & _TRUE)
        evidence["false_values"] = sorted(lowered & _FALSE)
        evidence["note"] = (
            "An Enterprise Geodatabase has no boolean type. Stored as SHORT with 1/0; "
            "the attribute table shows a number and cannot show that it was a boolean."
        )
        return "SHORT", None, evidence

    stripped = [v.strip() for v in as_text]

    if all(_INT.match(v) for v in stripped):
        numbers = [int(v) for v in stripped]
        evidence["reason"] = "every value is an integer literal"
        evidence["min"] = min(numbers)
        evidence["max"] = max(numbers)
        evidence["note"] = (
            "LONG regardless of the measured range. SHORT would fit here only as long as "
            "no later row exceeds it; edit the contract to SHORT deliberately if that is a "
            "constraint of the data rather than an accident of this sample."
        )
        return "LONG", None, evidence

    if all(_DECIMAL.match(v) for v in stripped):
        numbers = [float(v) for v in stripped]
        decimals = max((len(v.partition(".")[2].partition("e")[0]) for v in stripped), default=0)
        evidence["reason"] = "every value is a numeric literal and at least one is decimal"
        evidence["min"] = min(numbers)
        evidence["max"] = max(numbers)
        evidence["max_decimals"] = decimals
        evidence["note"] = (
            "DOUBLE, never FLOAT. A 32-bit float carries about 7 significant decimal "
            "digits, which silently rounds a 5-decimal latitude or an EPSG:3857 metre "
            "value - a plausible-looking coordinate in the wrong place."
        )
        return "DOUBLE", None, evidence

    if all(_ISO_DATE.match(v) for v in stripped):
        evidence["reason"] = "every value matches ISO 8601 date or date-time"
        evidence["min"] = min(stripped)
        evidence["max"] = max(stripped)
        return "DATE", None, evidence

    max_len = max(len(v) for v in as_text)
    length = text_length_for(max_len, headroom)
    evidence["reason"] = "values are not uniformly boolean, numeric or ISO 8601 dates"
    evidence["max_length"] = max_len
    evidence["length_headroom"] = headroom
    evidence["note"] = (
        f"TEXT length {length} = the measured maximum {max_len} times {headroom}, rounded up "
        f"to a multiple of {TEXT_LENGTH_STEP}. The measurement is a floor, not the answer: "
        "the next batch of data is longer."
    )
    return "TEXT", length, evidence


def declared_field(
    source_name: str, declared: dict[str, Any], values: list[Any]
) -> tuple[str, int | None, dict[str, Any]]:
    """Take the source's own declared type, and measure the data anyway.

    A FeatureSet exported from a geodatabase knows its schema better than any
    inference does - `state_fips` is TEXT(2) because somebody declared it so,
    not because the two-character sample happened to be two characters. So the
    declaration wins.

    The measurement is still taken and recorded next to it, for two reasons.
    CLAUDE.md section 4: reference data is data too, and a declared schema is
    reference data. And one disagreement is not a difference of opinion but a
    defect: a declared TEXT length that the source's own values exceed would
    fail at insert time, hundreds of rows in, so it is refused here instead.
    """
    esri_type = declared.get("type")
    keyword = ESRI_FIELD_TYPE_KEYWORD.get(esri_type)
    if keyword is None:
        raise SchemaError(
            f"field {source_name!r} is declared as {esri_type!r}, which this importer does not "
            "emit. Drop the field, or re-run with --infer-types to measure it instead of "
            "trusting the declaration."
        )

    measured_keyword, _, evidence = infer_field(source_name, values, headroom=1.0)

    # `infer_field` filled in its own reasoning for a decision that is not being
    # taken. Drop it rather than leave a note that contradicts the type above -
    # the measurement's *numbers* stay, its conclusion does not.
    for stale in ("note", "length_headroom", "reason"):
        evidence.pop(stale, None)

    evidence["declared_type"] = esri_type
    evidence["measured_type"] = measured_keyword
    evidence["reason"] = f"type taken from the source's own fields block: {esri_type}"

    if measured_keyword != keyword:
        evidence["declaration_overrides_measurement"] = (
            f"measuring the values alone would have chosen {measured_keyword}; the source "
            f"declares {keyword}. The declaration wins, and here it is right: a value like "
            "'01' measures as an integer and is a string with a leading zero, which LONG "
            "would silently destroy."
        )

    length = None
    if keyword == "TEXT":
        length = declared.get("length") or GLOBALID_TEXT_LENGTH
        measured_max = evidence.get("max_length")
        if measured_max is None:
            present = [v for v in values if not is_absent(v)]
            measured_max = max((len(str(v)) for v in present), default=0)
            evidence["max_length"] = measured_max
        evidence["declared_length"] = declared.get("length")
        if measured_max > length:
            raise SchemaError(
                f"field {source_name!r} is declared TEXT({length}) by the source, but the "
                f"source's own longest value is {measured_max} characters. The declaration and "
                "the data disagree, and the data wins at insert time - hundreds of rows in. "
                "Fix the source or re-run with --infer-types."
            )
        evidence["length_margin"] = length - measured_max
        evidence.setdefault(
            "note",
            f"TEXT({length}) is the length the source declares, not a padded measurement. "
            f"Its own longest value is {measured_max} characters, leaving "
            f"{length - measured_max} spare.",
        )

    if esri_type in ESRI_MANAGED_SOURCE_TYPES:
        evidence["carried_as"] = keyword
        evidence["note"] = ESRI_MANAGED_SOURCE_TYPES[esri_type]
        evidence["rename_recommended"] = f"source_{source_name.lower()}"

    return keyword, length, evidence


def build_fields(
    columns: list[str],
    rows: list[dict[str, Any]],
    *,
    exclude: Iterable[str] = (),
    headroom: float = DEFAULT_TEXT_HEADROOM,
    renames: dict[str, str] | None = None,
    declared: dict[str, dict[str, Any]] | None = None,
) -> list[FieldSpec]:
    """Build a FieldSpec for every column except the ones carrying the geometry.

    `renames` maps a source column name to the name it should take, and exists
    because `input/` is read-only: a source carrying a column literally called
    `objectid` cannot be edited, and the geodatabase manages that name itself.
    An unused rename is an error rather than a no-op - a mistyped one that
    silently does nothing is worse than one that fails.

    `declared` maps a source column to the source's own field declaration, when
    it has one. Where present it decides the type; the measurement is recorded
    beside it either way.
    """
    excluded = {c for c in exclude}
    renames = dict(renames or {})
    unused = [old for old in renames if old not in columns]
    if unused:
        raise SchemaError(
            f"--rename names {', '.join(repr(u) for u in unused)}, which is not a column in the "
            f"source. Columns are: {', '.join(columns)}"
        )

    taken: list[str] = []
    specs: list[FieldSpec] = []
    for column in columns:
        if column in excluded:
            continue
        values = [row.get(column) for row in rows]
        declaration = (declared or {}).get(column)
        if declaration is not None:
            esri_type, length, evidence = declared_field(column, declaration, values)
        else:
            esri_type, length, evidence = infer_field(column, values, headroom=headroom)

        requested = renames.get(column)
        name = sanitize_name(requested or column, taken)
        taken.append(name)
        if requested is not None:
            evidence["renamed_from"] = column
            evidence["rename_requested"] = requested
        elif name != column:
            evidence["renamed_from"] = column
        specs.append(
            FieldSpec(
                name=name,
                source=column,
                type=esri_type,
                length=length,
                nullable=evidence["nulls"] > 0,
                evidence=evidence,
            )
        )
    return specs
