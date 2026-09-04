#!/usr/bin/env python3
"""One-off provisioning script: build a synthetic Esri JSON airport FeatureSet.

**Why this script exists at all is the finding, not the code.**

The original input was `opensearch/input/airports.json`, an export from an
existing feature class in an Enterprise Geodatabase. It arrived with no licence
statement. It is very likely derived from the FAA airport data - "probably the
FAA data set, but I don't know for sure" - and "probably" is not a licence.
CLAUDE.md section 3 says to check the licence before the geometry, section 11
says everything in this repository has to be publishable under CC BY 4.0. So
the export is gitignored and never committed, and what was taken from it is its
**structure**:

- the `fields` array verbatim - names, `esriFieldType*`, string `length`
- `fieldAliases`, `displayFieldName`, `geometryType`, `spatialReference`
- geometry carried as `{"x": ..., "y": ...}` in metres and nothing else
- the *measured shape* of its quirks and distributions (see QUIRKS below)

Every value is generated here. No name, no code, no coordinate, no attribute
value comes from the original file. What does stay real is public fact that no
database can own: US state names and the official FIPS state codes, which are a
US government standard in the public domain.

A repository about generating test data, blocked by an unclear licence and
generating the data set instead, is the thesis of the whole talk happening by
itself rather than being asserted.

**This is a provisioning script, not part of the pipeline.** It writes an
`input/` fixture, which `input/` is otherwise forbidden to receive - CLAUDE.md
section 3 allows exactly this: a documented one-off script that creates an
input fixture and writes its own provenance and licence into the file. Its
output is committed, so it normally never runs again. `index_airports.py` reads
that committed fixture and never calls this script.

**Geometry, and why boxes rather than polygons.** Points are sampled inside
small hand-written latitude/longitude rectangles, one or more per state. Real
state boundaries would be the better sampling domain, and they would need a
licence - the same wall that removed the original data. So: rectangles, kept
small and inland precisely because CLAUDE.md section 4 warns that a bounding
box is not a boundary. Five boxes for Alaska and four for Hawaii instead of one
each, because a single rectangle around either is mostly ocean.

Two more rules from that section apply and are followed here:

- **`sin(latitude)` is sampled uniformly, not `latitude`.** A degree of
  longitude shortens towards the poles, so uniform latitude over-samples the
  high ones - which would visibly distort Alaska, the largest quota in the set.
- **Round before projecting.** Geographic coordinates are rounded to six
  decimals first, and the metre values are computed from the rounded numbers.
  The fixture then stores only x/y, exactly as the original export does, and a
  reader that inverts them gets the rounded degrees back.

Determinism: everything derives from `--seed`, including the GUIDs. The place
names and suffixes are LLM-generated (Claude Opus 5, 2026-09-04) and frozen
into this file as literals, so the non-determinism of generation is confined to
the moment they were written down rather than living in every run.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from webmercator import to_web_mercator  # noqa: E402  (path shim first)

# --------------------------------------------------------------------------
# Structure taken from the original export. Field names, Esri types and string
# lengths verbatim; this is schema, not data.
# --------------------------------------------------------------------------
SOURCE_FIELDS = [
    {"name": "objectid", "type": "esriFieldTypeInteger", "alias": "objectid"},
    {"name": "locid", "type": "esriFieldTypeString", "alias": "locid", "length": 5},
    {"name": "name", "type": "esriFieldTypeString", "alias": "name", "length": 45},
    {"name": "field", "type": "esriFieldTypeString", "alias": "field", "length": 30},
    {"name": "state", "type": "esriFieldTypeString", "alias": "state", "length": 24},
    {
        "name": "state_fips",
        "type": "esriFieldTypeString",
        "alias": "state_fips",
        "length": 2,
    },
    {"name": "acais", "type": "esriFieldTypeString", "alias": "acais", "length": 1},
    {"name": "tot_enp", "type": "esriFieldTypeDouble", "alias": "tot_enp"},
    {"name": "type", "type": "esriFieldTypeString", "alias": "type", "length": 20},
    {
        "name": "globalid",
        "type": "esriFieldTypeString",
        "alias": "globalid",
        "length": 38,
    },
    {"name": "ESRI_OID", "type": "esriFieldTypeOID", "alias": "ESRI_OID", "length": 8},
]

ATTRIBUTE_ORDER = [field["name"] for field in SOURCE_FIELDS]

# Measured in the original, reproduced here. Each of these is a trap that a
# tidier synthetic data set would have quietly removed - which is why they are
# in. The counts are for the default 880 features and scale with --count.
QUIRKS = {
    "blank_is_a_single_space": {
        "field": 825,
        "type": 453,
        "acais": 65,
        "note": "The geodatabase stores ' ', not NULL and not ''. In OpenSearch "
        "that is a real keyword term; in ArcGIS the cell looks empty and is not, "
        "so a filter on 'empty' finds nothing.",
    },
    "state_is_sometimes_a_code": {
        "values": ["HI", "MP"],
        "note": "Two of 57 state values are abbreviations where the rest are "
        "spelled out - and 'HI' here is FIPS 74 (US Minor Outlying Islands), not "
        "FIPS 15 (Hawaii). Filtering state='HI' returns points ~4,000 km from "
        "Hawaii; filtering state='Hawaii' loses them entirely.",
    },
    "one_fips_two_names": {
        "fips": "74",
        "names": ["HI", "Wake Island"],
        "note": "The same FIPS code carries two different state values.",
    },
    "two_unequal_object_ids": {
        "note": "`objectid` and `ESRI_OID` are both 1..N and both unique, and "
        "they agree in zero rows. The field called objectid is not the object "
        "id; the stable key is the business key `locid`.",
    },
    "duplicate_names": {
        "count": 3,
        "note": "`name` is not unique. 3 of 880 values occur twice.",
    },
    "integral_doubles": {
        "note": "`tot_enp` is esriFieldTypeDouble and every value is integral. "
        "The source schema defines the type, not the look of the values.",
    },
    "fips_has_leading_zeros": {
        "note": "289 of 880 state_fips values start with '0'. Never numeric.",
    },
}

# --------------------------------------------------------------------------
# Sampling domain. (state, fips, quota, region, [boxes]) with each box as
# (lat_min, lat_max, lon_min, lon_max) in EPSG:4326 degrees.
#
# State names and FIPS codes are public fact. The quotas reproduce the measured
# per-state distribution of the original, which is what puts 181 of 880 points
# in Alaska and therefore keeps the antimeridian span the whole use case turns
# on. The rectangles are hand-written, deliberately small, and deliberately not
# boundaries.
# --------------------------------------------------------------------------
STATE_QUOTAS: list[tuple[str, str, int, str, list[tuple[float, float, float, float]]]] = [
    ("Alaska", "02", 181, "alaska", [
        (54.70, 58.40, -136.90, -130.10),   # southeast panhandle
        (59.50, 62.30, -152.50, -142.00),   # south-central
        (63.00, 67.00, -156.00, -141.50),   # interior
        (68.30, 71.30, -159.90, -142.00),   # north slope
        (51.30, 55.50, -178.90, -162.00),   # aleutians
    ]),
    ("California", "06", 47, "conus", [(33.00, 41.00, -122.00, -117.00)]),
    ("Texas", "48", 41, "conus", [(29.00, 35.80, -102.40, -95.00)]),
    ("Florida", "12", 34, "conus", [(26.00, 30.50, -85.40, -80.60)]),
    ("Michigan", "26", 30, "conus", [
        (41.90, 45.50, -86.20, -83.20),     # lower peninsula
        (45.80, 47.20, -89.50, -84.50),     # upper peninsula
    ]),
    ("New York", "36", 29, "conus", [(42.00, 44.60, -78.50, -73.60)]),
    ("Washington", "53", 21, "conus", [(46.20, 48.80, -123.40, -117.60)]),
    ("Illinois", "17", 20, "conus", [(38.00, 42.20, -90.20, -88.00)]),
    ("Pennsylvania", "42", 19, "conus", [(40.00, 41.80, -80.30, -75.50)]),
    ("Arizona", "04", 18, "conus", [(32.00, 36.50, -114.20, -109.30)]),
    ("Colorado", "08", 17, "conus", [(37.20, 40.80, -108.50, -102.60)]),
    ("North Carolina", "37", 17, "conus", [(34.90, 36.40, -83.50, -76.60)]),
    ("Montana", "30", 16, "conus", [(45.20, 48.80, -114.40, -105.00)]),
    ("New Mexico", "35", 16, "conus", [(32.30, 36.70, -108.50, -103.50)]),
    ("Ohio", "39", 16, "conus", [(39.20, 41.50, -84.60, -81.00)]),
    ("Wisconsin", "55", 15, "conus", [(43.00, 46.50, -92.00, -87.60)]),
    ("Georgia", "13", 14, "conus", [(31.00, 34.70, -85.00, -81.50)]),
    ("Virginia", "51", 14, "conus", [(36.80, 39.00, -82.50, -76.60)]),
    ("Hawaii", "15", 13, "hawaii", [
        (21.90, 22.20, -159.70, -159.35),   # kauai
        (21.25, 21.70, -158.20, -157.70),   # oahu
        (20.60, 21.00, -156.60, -156.00),   # maui
        (19.00, 20.20, -155.90, -155.10),   # hawaii island
    ]),
    ("Kansas", "20", 13, "conus", [(37.20, 39.80, -101.50, -95.20)]),
    ("Minnesota", "27", 13, "conus", [(44.00, 48.50, -96.00, -92.00)]),
    ("Alabama", "01", 12, "conus", [(31.00, 34.80, -88.20, -85.40)]),
    ("Indiana", "18", 12, "conus", [(38.20, 41.60, -87.30, -85.00)]),
    ("Missouri", "29", 12, "conus", [(36.80, 40.40, -94.50, -90.50)]),
    ("Idaho", "16", 11, "conus", [(42.30, 48.00, -116.50, -112.00)]),
    ("Iowa", "19", 11, "conus", [(41.00, 43.30, -95.80, -91.50)]),
    ("Massachusetts", "25", 11, "conus", [(41.70, 42.70, -73.20, -70.60)]),
    ("Nebraska", "31", 11, "conus", [(40.30, 42.80, -103.50, -96.00)]),
    ("North Dakota", "38", 11, "conus", [(46.30, 48.80, -103.50, -97.20)]),
    ("Utah", "49", 11, "conus", [(37.50, 41.50, -113.40, -109.60)]),
    ("Wyoming", "56", 11, "conus", [(41.20, 44.80, -110.50, -104.60)]),
    ("Maine", "23", 10, "conus", [(43.60, 46.90, -70.70, -67.90)]),
    ("South Carolina", "45", 10, "conus", [(32.80, 34.90, -82.80, -79.60)]),
    ("Tennessee", "47", 10, "conus", [(35.20, 36.50, -89.40, -82.50)]),
    ("West Virginia", "54", 10, "conus", [(37.50, 39.80, -82.00, -78.50)]),
    ("Arkansas", "05", 9, "conus", [(33.30, 36.30, -94.30, -90.50)]),
    ("Louisiana", "22", 9, "conus", [(29.90, 32.70, -93.60, -90.00)]),
    ("Mississippi", "28", 9, "conus", [(31.00, 34.80, -91.00, -88.50)]),
    ("Oklahoma", "40", 9, "conus", [(34.20, 36.80, -100.50, -95.00)]),
    ("Oregon", "41", 9, "conus", [(42.20, 45.80, -123.40, -118.00)]),
    ("Puerto Rico", "72", 9, "caribbean", [(17.95, 18.45, -67.10, -65.70)]),
    ("South Dakota", "46", 9, "conus", [(43.20, 45.80, -103.80, -97.00)]),
    ("Kentucky", "21", 8, "conus", [(37.00, 38.90, -88.50, -83.00)]),
    ("Nevada", "32", 8, "conus", [(36.20, 41.60, -119.00, -115.00)]),
    ("New Jersey", "34", 8, "conus", [(39.50, 41.00, -75.10, -74.10)]),
    ("Maryland", "24", 7, "conus", [(38.40, 39.60, -79.20, -76.10)]),
    ("Connecticut", "09", 5, "conus", [(41.30, 41.90, -73.40, -72.00)]),
    ("New Hampshire", "33", 4, "conus", [(43.00, 44.70, -72.20, -71.00)]),
    ("American Samoa", "60", 3, "samoa", [(-14.38, -14.16, -170.85, -169.42)]),
    ("MP", "69", 3, "pacific", [(14.10, 15.30, 145.12, 145.85)]),
    ("Rhode Island", "44", 3, "conus", [(41.40, 41.90, -71.80, -71.25)]),
    ("Delaware", "10", 2, "conus", [(38.60, 39.70, -75.70, -75.15)]),
    ("Guam", "66", 2, "pacific", [(13.25, 13.65, 144.62, 144.95)]),
    # FIPS 74 is US Minor Outlying Islands. The original carries it under two
    # different state values, one of them the abbreviation of a different state.
    ("HI", "74", 2, "outlying", [
        (28.18, 28.23, -177.40, -177.34),   # midway-like
        (16.71, 16.75, -169.55, -169.50),   # johnston-like
    ]),
    ("Vermont", "50", 2, "conus", [(43.00, 44.80, -73.20, -72.10)]),
    ("Virgin Islands", "78", 2, "caribbean", [(17.70, 18.40, -65.05, -64.60)]),
    ("Wake Island", "74", 1, "pacific", [(19.27, 19.30, 166.60, 166.66)]),
]

# Coarse regional envelopes, one per region used above. The verifier reads
# these from the manifest and asserts that their union matches every document
# while the axis-transposed union matches none. Explicitly a *consistency*
# check against this generator's own definition - the independent checks are
# the reprojection and the coordinate provenance, and pretending otherwise
# would be worse than saying where the independence actually sits.
REGION_BOXES = {
    "conus":     (24.00, 49.50, -125.00, -66.50),
    "alaska":    (51.00, 71.50, -179.50, -129.50),
    "hawaii":    (18.80, 22.40, -160.00, -154.70),
    "pacific":   (13.00, 19.50,  144.50,  167.10),
    "samoa":     (-14.50, -14.10, -171.00, -169.30),
    "caribbean": (17.60, 18.60, -67.40, -64.50),
    "outlying":  (16.60, 28.40, -177.60, -169.40),
}

# --------------------------------------------------------------------------
# Vocabulary. LLM-generated (Claude Opus 5, 2026-09-04) and frozen as literals
# so that a run is reproducible. The place names are invented; any resemblance
# to a real airfield is coincidence, and none of them came from the original.
# --------------------------------------------------------------------------
PLACE_NAMES = [
    "Ashfall", "Amberton", "Arrowhead", "Bellhollow", "Birchmere", "Blackwater",
    "Bluewing", "Bracken", "Brightwater", "Cairnfield", "Canterhill", "Cedarloft",
    "Chalkridge", "Cinderbrook", "Clearmont", "Cloverdyke", "Coldharbor",
    "Copperline", "Cranemoor", "Crestwater", "Dunmarsh", "Dustbowl Flats",
    "Eastmarch", "Elkhollow", "Ellsworth Bend", "Emberfield", "Fairhaven Flats",
    "Fallowmere", "Farnsley", "Fernbrake", "Flintlow", "Foxbarrow", "Frostmill",
    "Gales End", "Glasswater", "Goldmarsh", "Granite Fork", "Graylock",
    "Greenspire", "Hallowfield", "Harrowgate", "Hawthorne Rise", "Hazelbrook",
    "Hemlock Draw", "Highwater", "Hollowpine", "Ironbark", "Jasper Reach",
    "Junipero Flats", "Kelphaven", "Kestrel Point", "Lanternhill", "Larkmoor",
    "Lattimore", "Limestone Gap", "Longwharf", "Lyndenbrook", "Marrowvale",
    "Meadowlark", "Millbrace", "Mistlow", "Moorcroft", "Mossgate",
    "Northreach", "Oakenshaw", "Orchard Bend", "Otterbourne", "Palewater",
    "Pemberly Flats", "Pineholt", "Quarrymouth", "Quillhaven", "Ramsgate Bar",
    "Ravensmoor", "Redcliff Landing", "Ridgewater", "Rooksbridge", "Rushmere",
    "Saltmarsh Bend", "Sandpiper Key", "Selkirk Flats", "Shalebrook",
    "Silverbirch", "Slatewell", "Sorrelfield", "Southgate Downs", "Sparrowvale",
    "Stillwater Gap", "Stonemill", "Sumac Ridge", "Sweetbriar", "Tallowmere",
    "Thistledown", "Thornbury", "Tidewater Flats", "Timberfall", "Trellisford",
    "Underhill", "Vantage Point", "Verdigris", "Wainwright Bar", "Waterloo Gap",
    "Westermoor", "Wheatstone", "Whiteholm", "Wickerbrook", "Wildergrove",
    "Willowmere", "Windrow", "Winterbourne", "Wolfsbane Flats", "Wrenfield",
    "Yarrowmead", "Yewbank", "Zephyr Basin",
    # Longer names on purpose: `name` is declared with length 45 and the
    # original's longest value is 44 characters, so the column is fully used.
    # A fixture whose longest name is 28 characters would let a too-narrow
    # ArcGIS text column look fine.
    "Kettleborough Crossing", "Marchmont Bridgewater", "Saint Aubrey Harbour",
    "Cranborne Wetherfield", "Nettlestone Priorsgate", "Ashcombe Fitzharding",
    "Thorncastle Wilmington", "Greatstone Underbridge", "Fennimore Blackstock",
    "Rowanbridge Aldercreek",
]

# Suffix vocabulary in the shape the original uses: heavily abbreviated, mixed
# civil and military, some of them just "Field".
NAME_SUFFIXES = [
    "Intl", "Muni", "Field", "Regional", "Airpark", "Air Terminal",
    "Mem", "AS", "NAF", "AAF", "County", "Landing",
]

# `field` in the original is populated on 55 of 880 rows with values 10-26
# characters long. Same shape, invented values.
FIELD_VALUES = [
    "Coastal District", "Northern Sector", "Inland Basin", "Upper Valley",
    "Tidewater Region", "Highland Reach", "Southern Plains", "Great Divide",
    "Lakeshore Belt", "Desert Corridor", "Riverine District", "Border Sector",
    "Alpine Reach", "Prairie Belt", "Delta District", "Windward Sector",
    "Leeward Reach", "Piedmont Belt", "Basin and Range", "Gulf Approach",
    "Arctic Sector", "Interior Reach", "Panhandle Belt", "Island Group",
    "Sound District", "Cascade Corridor", "Front Range Belt", "Badlands Sector",
    "Bayou District", "Sandhills Reach", "Peninsula Sector", "Escarpment Belt",
    "Watershed District", "Mesa Corridor", "Bluffside Reach", "Moraine Belt",
    "Estuary District", "Foothills Sector", "Karst Region", "Outwash Plain",
    "Rift Corridor", "Barrier Island", "Terrace District", "Drumlin Belt",
    "Playa Sector", "Coulee Reach", "Fjord District", "Tundra Sector",
    "Chaparral Belt", "Savanna Reach", "Muskeg District", "Steppe Corridor",
    "Cordillera Belt", "Archipelago Zone",
]

# Six values including the single space, at the measured proportions. The
# distribution is markedly skewed - 146 International against 23 Seaplane Base
# - and a round-robin fill would have flattened it into five equal buckets, so
# every classification, legend and histogram built on the fixture would have
# looked wrong for reasons nobody could name.
AIRPORT_TYPE_QUOTAS = [
    ("International", 146),
    ("Regional", 98),
    ("Municipal", 96),
    ("Military", 64),
    ("Seaplane Base", 23),
]
AIRPORT_TYPES = [name for name, _quota in AIRPORT_TYPE_QUOTAS]

BLANK = " "  # the geodatabase's idea of empty

DEFAULT_SEED = 20260904
DEFAULT_COUNT = 880

# Decimals kept on the projected metre values, and the reason the number is not
# "as many as the double has".
#
# Measured: rebuilding this fixture on Windows (CPython 3.14.7, MSVC) against
# Linux (CPython 3.12.7, glibc) produced a different SHA-256 at identical size
# and feature count. Same seed, and the Mersenne Twister reproduced
# bit-for-bit - the divergence was 30 of 880 `y` values differing by up to
# **2 ULP, 1.9 nanometres**. `x = R * radians(lon)` is a multiplication and was
# identical everywhere; `y = R * log(tan(pi/4 + phi/2))` passes through libm
# twice, and C transcendental functions are not standardised to the last bit.
#
# Storing the raw double carried that bit into the file, so a committed fixture
# pinned by its hash could not be rebuilt on another platform. Rounding to four
# decimals - a tenth of a millimetre, and the precision the original
# geodatabase export actually carried - puts the difference below the stored
# resolution. `self_check` verifies that no value sits close enough to a
# rounding boundary for the two platforms to round it in different directions.
METRE_DECIMALS = 4

# How far a metre value must stay from a .5 rounding boundary for the rounding
# itself to be platform-stable. 10 nm is ~5x the 1.9 nm divergence measured
# between glibc and MSVC. At the committed seed the closest value clears it by
# a factor of 2.9, and clears the measured divergence by 15.6x. At six decimals
# it would not have cleared it at all - the nearest value sits 0.5x away, which
# is why this is checked rather than assumed.
ROUNDING_BOUNDARY_MARGIN_M = 1e-8


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------
def scaled_quotas(count: int) -> list[tuple[str, str, int, str, list]]:
    """Scale the measured per-state distribution to `count` features.

    Largest-remainder, so the total is exact and the ordering of the table
    decides who gets the leftovers. Every state keeps at least one feature -
    losing Wake Island to rounding would remove the antimeridian point the
    whole use case is about.
    """
    total = sum(quota[2] for quota in STATE_QUOTAS)
    if count < len(STATE_QUOTAS):
        raise SystemExit(
            f"error: --count {count} is below the {len(STATE_QUOTAS)} states in "
            "the distribution; every state must keep at least one feature"
        )
    exact = [(quota, quota[2] * count / total) for quota in STATE_QUOTAS]
    floors = [max(1, int(value)) for _, value in exact]
    remainder = count - sum(floors)
    # Hand out (or take back) the remainder by largest fractional part.
    order = sorted(
        range(len(exact)),
        key=lambda i: (exact[i][1] - int(exact[i][1]), -i),
        reverse=remainder > 0,
    )
    step = 1 if remainder > 0 else -1
    position = 0
    while remainder != 0:
        index = order[position % len(order)]
        if step < 0 and floors[index] <= 1:
            position += 1
            continue
        floors[index] += step
        remainder -= step
        position += 1
    return [
        (name, fips, floors[i], region, boxes)
        for i, (name, fips, _, region, boxes) in enumerate(STATE_QUOTAS)
    ]


def sample_point(rng: random.Random, box: tuple[float, float, float, float]):
    """Sample one point in a lat/lon box, uniform *on the ground*.

    `sin(latitude)` is sampled uniformly rather than `latitude`: a degree of
    longitude shortens towards the poles, so uniform latitude would crowd the
    high latitudes. Over Alaska's 20 degrees of latitude that is a visible
    distortion, not a rounding detail. Returns rounded degrees - CLAUDE.md
    section 4: round before projecting, so the stored metres and the degrees a
    reader recovers from them cannot disagree by the rounding step.
    """
    lat_min, lat_max, lon_min, lon_max = box
    sin_min, sin_max = math.sin(math.radians(lat_min)), math.sin(math.radians(lat_max))
    latitude = math.degrees(math.asin(rng.uniform(sin_min, sin_max)))
    longitude = rng.uniform(lon_min, lon_max)
    return round(latitude, 6), round(longitude, 6)


def make_locids(rng: random.Random, count: int) -> list[str]:
    """Unique location codes in the shape the original uses.

    Measured there: 877 of 880 are three characters, 3 are four, and 56 contain
    a digit. Same proportions, invented codes.
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    long_codes = max(1, round(count * 3 / 880))
    with_digit = max(1, round(count * 56 / 880))
    codes: list[str] = []
    seen: set[str] = set()
    while len(codes) < count:
        position = len(codes)
        length = 4 if position < long_codes else 3
        if position < long_codes + with_digit:
            # A digit anywhere but the first character, as in the original.
            body = [rng.choice(letters)] + [
                rng.choice(letters + "0123456789") for _ in range(length - 1)
            ]
            code = "".join(body)
            if not any(character.isdigit() for character in code):
                code = code[:-1] + rng.choice("0123456789")
        else:
            code = "".join(rng.choice(letters) for _ in range(length))
            if any(character.isdigit() for character in code):
                continue
        if code in seen:
            continue
        seen.add(code)
        codes.append(code)
    rng.shuffle(codes)
    return codes


def make_names(rng: random.Random, count: int, duplicates: int) -> list[str]:
    """Airport names, with a measured number of deliberate duplicates.

    `name` is not unique in the original - 3 of 880 values occur twice - which
    is the reason `locid` and not `name` is the identity key. A synthetic set
    with unique names would have hidden that.
    """
    combinations = [
        f"{place} {suffix}" for place in PLACE_NAMES for suffix in NAME_SUFFIXES
    ]
    if len(combinations) < count:
        raise SystemExit(
            f"error: the frozen vocabulary yields {len(combinations)} names, "
            f"fewer than the requested {count}"
        )
    rng.shuffle(combinations)
    unique_needed = count - duplicates
    names = combinations[:unique_needed]
    names.extend(rng.sample(names, duplicates))
    rng.shuffle(names)
    return names


def make_guid(rng: random.Random) -> str:
    """A registry-style GUID in braces, 38 characters, from the seeded RNG.

    `uuid.uuid4()` is deliberately not used: it draws from the OS entropy pool
    and would make the fixture different on every run, which is the one thing a
    committed fixture must not be.
    """
    digits = "".join(rng.choice("0123456789ABCDEF") for _ in range(32))
    return (
        f"{{{digits[:8]}-{digits[8:12]}-{digits[12:16]}-"
        f"{digits[16:20]}-{digits[20:]}}}"
    )


def derange(rng: random.Random, reference: list[int]) -> list[int]:
    """A permutation of the same values that agrees with `reference` nowhere.

    Reproduces the measured relationship between `objectid` and `ESRI_OID`:
    both are 1..N, both unique, and they are equal in zero rows.
    """
    candidate = reference[:]
    rng.shuffle(candidate)
    for index in range(len(candidate)):
        if candidate[index] != reference[index]:
            continue
        partner = (index + 1) % len(candidate)
        # Find a partner where swapping fixes this position without breaking it.
        for offset in range(1, len(candidate)):
            partner = (index + offset) % len(candidate)
            if (
                candidate[partner] != reference[index]
                and candidate[index] != reference[partner]
            ):
                break
        candidate[index], candidate[partner] = candidate[partner], candidate[index]
    return candidate


def make_enplanements(rng: random.Random, count: int) -> list[float]:
    """Passenger counts with the measured shape: log-normal, integral, min 100.

    Measured in the original: min 100, median 6,291, max 38,893,670 - five and
    a half orders of magnitude. A uniform draw would have produced a data set
    where no airport is small and none is Atlanta, and any classification built
    on it would look wrong for reasons nobody could name.
    """
    # sigma is set from the measured spread, not guessed: the maximum sits
    # roughly 3.1 standard deviations above the median in log space, so
    # sigma ~= (ln(38_893_670) - ln(6_291)) / 3.1. A narrower draw (1.85 was
    # the first attempt) produced a set whose largest airport was 3.7 million -
    # plausible-looking, and an order of magnitude short of the real tail.
    sigma = (math.log(38_893_670.0) - math.log(6291.0)) / 3.1
    values: list[float] = []
    for _ in range(count):
        magnitude = rng.lognormvariate(math.log(6291.0), sigma)
        # The clamps are the source's own: 100 is its minimum and looks like a
        # reporting cutoff, 38,893,670 its single busiest hub.
        values.append(float(min(38_893_670, max(100, round(magnitude)))))
    return values


def build_featureset(count: int, seed: int) -> dict:
    """Assemble the whole FeatureSet. Deterministic given `count` and `seed`."""
    rng = random.Random(seed)
    quotas = scaled_quotas(count)

    # Geometry first, so every downstream list is exactly as long as the set.
    positions: list[tuple[str, str, str, float, float]] = []
    for state, fips, quota, region, boxes in quotas:
        for index in range(quota):
            box = boxes[index % len(boxes)]
            latitude, longitude = sample_point(rng, box)
            positions.append((state, fips, region, latitude, longitude))
    rng.shuffle(positions)

    locids = make_locids(rng, count)
    duplicate_names = max(0, round(count * QUIRKS["duplicate_names"]["count"] / 880))
    names = make_names(rng, count, duplicate_names)
    enplanements = make_enplanements(rng, count)

    identifiers = list(range(1, count + 1))
    object_ids = identifiers[:]
    rng.shuffle(object_ids)
    esri_oids = derange(rng, object_ids)

    # The three quirk columns, built as full-length lists and then shuffled, so
    # the blank values are scattered rather than clustered at the front.
    blanks = QUIRKS["blank_is_a_single_space"]
    field_filled = count - max(0, round(count * blanks["field"] / 880))
    fields = [FIELD_VALUES[i % len(FIELD_VALUES)] for i in range(field_filled)]
    fields += [BLANK] * (count - field_filled)
    rng.shuffle(fields)

    type_blank = max(0, round(count * blanks["type"] / 880))
    typed = count - type_blank
    quota_total = sum(quota for _name, quota in AIRPORT_TYPE_QUOTAS)
    types: list[str] = []
    for name, quota in AIRPORT_TYPE_QUOTAS[:-1]:
        types += [name] * round(typed * quota / quota_total)
    # The last category absorbs the rounding, so the total is exact.
    last = AIRPORT_TYPE_QUOTAS[-1][0]
    types += [last] * max(0, typed - len(types))
    types = types[:typed]
    types += [BLANK] * (count - len(types))
    rng.shuffle(types)

    acais_blank = max(0, round(count * blanks["acais"] / 880))
    acais = ["Y"] * (count - acais_blank) + [BLANK] * acais_blank
    rng.shuffle(acais)

    features = []
    # Smallest distance between an *unrounded* metre value and the .5 boundary
    # it is about to be rounded across. Measured here because after rounding
    # every value sits exactly on the grid and the question can no longer be
    # asked - a check on the rounded values would always pass and prove
    # nothing. Carried into `_provenance` so `self_check` can assert it and so
    # the fixture records how much room its own hash has.
    rounding_margin = float("inf")
    step = 10.0 ** -METRE_DECIMALS
    for index, (state, fips, _region, latitude, longitude) in enumerate(positions):
        x, y = to_web_mercator(longitude, latitude)
        for raw in (x, y):
            scaled = abs(raw) / step
            distance = abs((scaled - math.floor(scaled)) - 0.5) * step
            rounding_margin = min(rounding_margin, distance)
        # Rounded so the file does not carry libm's last bit - see
        # METRE_DECIMALS. The source export was rounded too.
        x, y = round(x, METRE_DECIMALS), round(y, METRE_DECIMALS)
        attributes = {
            "objectid": object_ids[index],
            "locid": locids[index],
            "name": names[index],
            "field": fields[index],
            "state": state,
            "state_fips": fips,
            "acais": acais[index],
            "tot_enp": enplanements[index],
            "type": types[index],
            "globalid": make_guid(rng),
            "ESRI_OID": esri_oids[index],
        }
        # Key order as the source export has it, so a diff against a real
        # export is about values rather than ordering.
        features.append(
            {
                "attributes": {name: attributes[name] for name in ATTRIBUTE_ORDER},
                "geometry": {"x": x, "y": y},
            }
        )

    return {
        "_provenance": {
            "synthetic": True,
            "generated_by": "opensearch/scripts/make_airports_fixture.py",
            "command": (
                f"python3 scripts/make_airports_fixture.py --seed {seed} "
                f"--count {count} --output input/synthetic_airports.json"
            ),
            "seed": seed,
            "model": "Claude Opus 5",
            "generated": "2026-09-04",
            "licence": "CC BY 4.0",
            "attribution": (
                "Synthetic test data from euro_dev_summit_26_test_data_ai, "
                "CC BY 4.0. Contains no third-party data."
            ),
            "structure_source": (
                "Field names, Esri field types, string lengths, fieldAliases, "
                "geometryType, spatialReference and the measured distributions "
                "and quirks were copied from an export of a feature class in an "
                "Enterprise Geodatabase. No values were copied."
            ),
            "why_synthetic": (
                "The original export carried no licence statement. It is "
                "probably derived from FAA airport data, but 'probably' is not "
                "a licence, and this repository is published under CC BY 4.0 "
                "(CLAUDE.md sections 3 and 11). The original is gitignored and "
                "never committed; only its structure was reused."
            ),
            "real_public_facts_retained": (
                "US state names and official FIPS state codes - a US government "
                "standard in the public domain."
            ),
            "not_real": (
                "Every coordinate, name, locid, globalid, objectid, ESRI_OID, "
                "tot_enp, type, acais and field value is generated. Place names "
                "are invented; resemblance to a real airfield is coincidence."
            ),
            "sampling": (
                "Points are drawn inside hand-written lat/lon rectangles, "
                "uniform in sin(latitude) for equal-area coverage, rounded to 6 "
                "decimals and then projected to EPSG:3857. Rectangles are not "
                "boundaries - real state polygons would have needed a licence."
            ),
            "metre_decimals": METRE_DECIMALS,
            "rounding_margin_m": rounding_margin,
            "rounding_margin_note": (
                "Smallest distance between an unrounded projected value and the "
                "rounding boundary it crosses. Must exceed "
                f"{ROUNDING_BOUNDARY_MARGIN_M:.0e} m, or two platforms whose "
                "libm differs in the last bit could round a value in opposite "
                "directions and this file's SHA-256 would not be reproducible. "
                "Measured divergence between glibc and MSVC: 2 ULP, 1.9e-09 m, "
                "on 30 of 880 y values."
            ),
            "region_boxes": REGION_BOXES,
            "quirks_reproduced": QUIRKS,
        },
        "displayFieldName": "",
        "fieldAliases": {field["name"]: field["alias"] for field in SOURCE_FIELDS},
        "geometryType": "esriGeometryPoint",
        "spatialReference": {"wkid": 102100, "latestWkid": 3857},
        "fields": SOURCE_FIELDS,
        "features": features,
    }


def self_check(featureset: dict) -> list[str]:
    """Assert the fixture actually has the properties it claims.

    A generator that silently drifts produces a fixture whose manifest lies,
    and every check downstream then verifies the wrong thing. Cheap insurance,
    and it runs on every invocation rather than on request.
    """
    problems: list[str] = []
    features = featureset["features"]
    attributes = [feature["attributes"] for feature in features]

    for column in ("locid", "globalid", "objectid", "ESRI_OID"):
        values = [row[column] for row in attributes]
        if len(set(values)) != len(values):
            problems.append(f"{column} is not unique")

    equal = sum(1 for row in attributes if row["objectid"] == row["ESRI_OID"])
    if equal:
        problems.append(f"objectid equals ESRI_OID in {equal} rows, expected 0")

    for field in SOURCE_FIELDS:
        limit = field.get("length")
        if limit is None:
            continue
        too_long = [
            row[field["name"]]
            for row in attributes
            if len(str(row[field["name"]])) > limit
        ]
        if too_long:
            problems.append(
                f"{field['name']} exceeds its declared length {limit}: "
                f"{too_long[0]!r}"
            )

    if not all(float(row["tot_enp"]).is_integer() for row in attributes):
        problems.append("tot_enp has non-integral values")

    # Every point must sit inside the regional envelope of its own state, and
    # the manifest publishes those envelopes for the verifier to re-check.
    #
    # The comparison happens in metres, by projecting the box corners forward,
    # rather than by inverting the stored x/y. Web Mercator is monotonic in
    # both axes, so the two are equivalent - and this way the inverse formula
    # exists in exactly one place in the repository, `index_airports.py`, which
    # is the script whose inverse the verifier is meant to be checking. A copy
    # here would be a third implementation nobody audits.
    region_of = {state: region for state, _f, _q, region, _b in STATE_QUOTAS}
    outside = 0
    for feature, row in zip(features, attributes):
        lat_min, lat_max, lon_min, lon_max = REGION_BOXES[region_of[row["state"]]]
        x_min, y_min = to_web_mercator(lon_min, lat_min)
        x_max, y_max = to_web_mercator(lon_max, lat_max)
        x, y = feature["geometry"]["x"], feature["geometry"]["y"]
        if not (x_min <= x <= x_max and y_min <= y <= y_max):
            outside += 1
    if outside:
        problems.append(f"{outside} points fall outside their own region box")

    fips_names: dict[str, set[str]] = {}
    for row in attributes:
        fips_names.setdefault(row["state_fips"], set()).add(row["state"])
    if not any(len(names) > 1 for names in fips_names.values()):
        problems.append("no FIPS code carries two state names - quirk lost")

    # Was any unrounded value close enough to a rounding boundary that two
    # platforms disagreeing in the last bit could round it in opposite
    # directions? The margin is measured in `build_featureset`, on the values
    # before rounding - asking the rounded values would always pass, because
    # rounding puts them on the grid by definition.
    margin = featureset["_provenance"]["rounding_margin_m"]
    if margin < ROUNDING_BOUNDARY_MARGIN_M:
        problems.append(
            f"an unrounded projected value sits {margin:.3e} m from a rounding "
            f"boundary at {METRE_DECIMALS} decimals, inside the "
            f"{ROUNDING_BOUNDARY_MARGIN_M:.0e} m margin. Two platforms whose "
            "libm differs in the last bit could round it in opposite "
            "directions, so this file's SHA-256 would not be reproducible. "
            "Change --seed, or reduce METRE_DECIMALS"
        )

    return problems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="make_airports_fixture.py",
        description=(
            "Build a synthetic Esri JSON point FeatureSet with the structure of "
            "an Enterprise Geodatabase export: {x, y} geometry in EPSG:3857 "
            "metres, esriFieldType* schema, and the measured quirks of the "
            "original - a single space for empty, two unequal object ids, a "
            "FIPS code with two state names, duplicate names. A one-off "
            "provisioning script: its output is committed, so it normally never "
            "runs again."
        ),
        epilog=(
            "Examples:\n"
            "  # rebuild the committed fixture exactly\n"
            "  python3 scripts/make_airports_fixture.py \\\n"
            "      --output input/synthetic_airports.json\n\n"
            "  # a smaller set for a quick experiment, into build/\n"
            "  python3 scripts/make_airports_fixture.py --count 100 \\\n"
            "      --output build/small_airports.json\n\n"
            "  # rebuild with the manifest alongside it\n"
            "  python3 scripts/make_airports_fixture.py \\\n"
            "      --output input/synthetic_airports.json \\\n"
            "      --manifest input/synthetic_airports_source.json\n\n"
            "The original export this structure came from is gitignored and "
            "unlicensed; see the module docstring. Index the fixture with "
            "scripts/index_airports.py."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="JSON",
        help="where to write the FeatureSet (required, no default: a flag that "
        "writes a file gets no convenient default)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        metavar="JSON",
        help="also write the provenance manifest here, including the SHA-256 of "
        "the FeatureSet and the region boxes the verifier reads",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        metavar="N",
        help="number of features; the measured per-state distribution is scaled "
        "to it and every state keeps at least one (default: %(default)s, the "
        "count of the original export)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        metavar="N",
        help="random seed - the committed fixture was built with the default "
        "(default: %(default)s)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    featureset = build_featureset(args.count, args.seed)

    problems = self_check(featureset)
    if problems:
        for problem in problems:
            print(f"error: self-check failed: {problem}", file=sys.stderr)
        return 3

    # Compact separators and an explicit "\n" newline, both on purpose. Compact
    # because that is what an `f=json` export looks like; explicit newline
    # because the fixture is pinned by SHA-256 in the manifest and a CRLF
    # translation on Windows would change the hash without changing the data.
    text = json.dumps(featureset, ensure_ascii=False, separators=(",", ":")) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(
        f"wrote {args.output} | {len(featureset['features']):,} features, "
        f"{len(text) / 1024:.1f} KB"
    )
    print(f"sha256 {digest}")

    if args.manifest:
        provenance = featureset["_provenance"]
        manifest = {
            "file": args.output.name,
            "features": len(featureset["features"]),
            "bytes": len(text.encode("utf-8")),
            "sha256": digest,
            "geometry_type": featureset["geometryType"],
            "spatial_reference": featureset["spatialReference"],
            "coordinate_units": "metres (EPSG:3857 / Web Mercator auxiliary sphere)",
            "metre_decimals": provenance["metre_decimals"],
            "rounding_margin_m": provenance["rounding_margin_m"],
            "rounding_margin_note": provenance["rounding_margin_note"],
            "generated_by": provenance["generated_by"],
            "command": provenance["command"],
            "seed": args.seed,
            "model": provenance["model"],
            "generated": provenance["generated"],
            "licence": provenance["licence"],
            "attribution": provenance["attribution"],
            "structure_source": provenance["structure_source"],
            "why_synthetic": provenance["why_synthetic"],
            "real_public_facts_retained": provenance["real_public_facts_retained"],
            "sampling": provenance["sampling"],
            "region_boxes_note": (
                "lat_min, lat_max, lon_min, lon_max in EPSG:4326 degrees. Read "
                "by verify_airports.py. Consistency reference, not an "
                "independent one - the independent checks are the reprojection "
                "and the coordinate provenance."
            ),
            "region_boxes": REGION_BOXES,
            "state_regions": {
                state: region for state, _f, _q, region, _b in STATE_QUOTAS
            },
            "quirks_reproduced": QUIRKS,
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {args.manifest} | manifest with the fixture's SHA-256")

    return 0


if __name__ == "__main__":
    sys.exit(main())
