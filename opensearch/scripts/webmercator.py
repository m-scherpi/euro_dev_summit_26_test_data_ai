"""Spherical Web Mercator, forward direction only (EPSG:4326 -> EPSG:3857).

**This module deliberately contains no inverse.** It is imported by
`make_airports_fixture.py`, which projects generated geographic coordinates
into the metre grid an Esri JSON export carries, and by `verify_airports.py`,
which projects the *indexed* geographic coordinates back into that same grid to
check them against the source values.

`index_airports.py` - the script actually under test, the one that has to turn
metres into degrees - writes its own inverse by hand and imports nothing from
here. That is the point: CLAUDE.md section 4 says a verifier must not share its
projection implementation with the generator it checks, because a bug then
passes both. The two directions are different expressions of different
functions, so agreement between them is evidence rather than tautology.

The failure mode this guards against is not random noise. A wrong Mercator is
systematically biased in one direction, which survives averaging and looks
entirely plausible in a table of coordinates.

EPSG:3857 is defined on a sphere of exactly the WGS 84 semi-major axis, with no
flattening - that is what makes it "auxiliary sphere" and what makes the
formula this short. Do not substitute a mean radius here; PROJ uses 6378137
for this CRS and so does every tile server.
"""

from __future__ import annotations

import math

# WGS 84 semi-major axis. EPSG:3857 uses it as a sphere radius on purpose.
EPSG_3857_RADIUS_M = 6378137.0

# Web Mercator is undefined at the poles - ln(tan(pi/4 + phi/2)) diverges - and
# is conventionally clipped at the latitude whose y equals the x extent.
MAX_LATITUDE_DEG = 85.051129


def to_web_mercator(longitude: float, latitude: float) -> tuple[float, float]:
    """Project geographic degrees to EPSG:3857 metres.

    Argument order is longitude first, matching GeoJSON and the array form of
    an OpenSearch geo_point (RFC 7946), and returning (x, y) in the same order.
    Naming both ends explicitly is cheaper than remembering which convention
    this particular function chose.
    """
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude {longitude} outside [-180, 180]")
    if abs(latitude) > MAX_LATITUDE_DEG:
        raise ValueError(
            f"latitude {latitude} outside +/-{MAX_LATITUDE_DEG}, where Web "
            "Mercator is undefined"
        )
    x = EPSG_3857_RADIUS_M * math.radians(longitude)
    y = EPSG_3857_RADIUS_M * math.log(
        math.tan(math.pi / 4.0 + math.radians(latitude) / 2.0)
    )
    return x, y
