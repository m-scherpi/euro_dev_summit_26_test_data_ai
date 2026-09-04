# The ArcGIS API for Python, and what it actually writes

Produced by `try_arcgis_api.py`. This is a measurement of one machine, not a claim
about every machine - which is the point, because the outcome depends entirely on
what is importable in the interpreter.

## Environment

| | |
|---|---|
| `python` | 3.12.7 |
| `executable` | build/venv_api/bin/python |
| `ARCGIS_IO_ENGINE` | (unset - the API picks the first available) |
| `arcpy` | NOT importable (ModuleNotFoundError) |
| `arcgis` | 2.4.1.1 |
| `pandas` | 2.2.3 |
| `osgeo.gdal` | NOT importable (ModuleNotFoundError) |
| `fiona` | NOT importable (ModuleNotFoundError) |
| `shapefile` | 2.3.1 |

## Route 1 - `GIS.content.import_data()`

**Not attempted, deliberately.** It produces a *hosted* feature layer in the ArcGIS
Data Store: the rows are copied out of the customer's database into Esri's own
relational store. The goal here is a feature class *in* PostgreSQL, so this route does
not fall short of the goal, it inverts it - and running it would upload the data to a
portal, which is not a side effect a verification script should have.

It is worth naming precisely because it is the route the API's own tutorials show, and
it succeeds. A reader following the documentation gets a working layer and no signal
that the data left the database.

## Route 2 - `DataFrame.spatial.to_featureclass()`

Esri's guide, verbatim:

> Writing to file geodatabases requires the ArcPy site-package.

<https://developers.arcgis.com/python/latest/guide/introduction-to-the-spatially-enabled-dataframe/>

| | |
|---|---|
| location requested | build/arcgis_api/nrw_points_api |
| rows | 100 |
| outcome | RETURNED A PATH |
| returned path | build/arcgis_api/nrw_points_api.shp |
| format written | SHAPEFILE |
| files created | `nrw_points_api.dbf`, `nrw_points_api.prj`, `nrw_points_api.shp`, `nrw_points_api.shx` |
| prj written | GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Deg |

**The call succeeded and wrote a shapefile. It was asked for a feature class. No exception, no warning - just a different format at the path it returned.**

### Schema: what the contract asked for, and what the API produced

`to_featureclass` takes `location, overwrite, has_z, has_m, sanitize_columns` and
nothing else. There is no parameter for a field type, a TEXT length or an alias, and
Esri publishes no dtype mapping table. For an importer whose deliverable *is* the
schema, that is disqualifying - which is why `import_to_egdb.py` calls
`CreateFeatureclass` and `AddField` and states every type and length itself.

| Contract field | Contract type | Written as | Written type |
|---|---|---|---|
| `id` | LONG | `id` | N(10,0) |
| `title` | TEXT(40) | `title` | C(255,0) |
| `description` | TEXT(120) | `descriptio` **renamed** | C(255,0) |
| `latitude` | DOUBLE | `latitude` | F(19,11) |
| `longitude` | DOUBLE | `longitude` | F(19,11) |
| `x_3857` | DOUBLE | `x_3857` | F(19,11) |
| `y_3857` | DOUBLE | `y_3857` | F(19,11) |
| `visitor_count` | LONG | `visitor_co` **renamed** | N(10,0) |
| `elevation_m` | DOUBLE | `elevation_` **renamed** | F(19,11) |
| `is_enchanted` | SHORT | `is_enchant` **renamed** | L(1,0) |

**What the schema lost on the way:**

- `description` was renamed to `descriptio` - silently truncated to the DBF field-name limit of 10 characters. Nothing in the call reports it, and a downstream query on the original name finds no column.
- `visitor_count` was renamed to `visitor_co` - silently truncated to the DBF field-name limit of 10 characters. Nothing in the call reports it, and a downstream query on the original name finds no column.
- `elevation_m` was renamed to `elevation_` - silently truncated to the DBF field-name limit of 10 characters. Nothing in the call reports it, and a downstream query on the original name finds no column.
- `is_enchanted` was renamed to `is_enchant` - silently truncated to the DBF field-name limit of 10 characters. Nothing in the call reports it, and a downstream query on the original name finds no column.
- `title`: the contract measured TEXT(40) from the data; the API wrote C(255) - the format's maximum, so the measurement was discarded rather than used.
- `description`: the contract measured TEXT(120) from the data; the API wrote C(255) - the format's maximum, so the measurement was discarded rather than used.
- `latitude`: DOUBLE became DBF type F (float). A shapefile has no double, so the geodatabase type the contract asked for does not exist in the format that was written instead.
- `longitude`: DOUBLE became DBF type F (float). A shapefile has no double, so the geodatabase type the contract asked for does not exist in the format that was written instead.
- `x_3857`: DOUBLE became DBF type F (float). A shapefile has no double, so the geodatabase type the contract asked for does not exist in the format that was written instead.
- `y_3857`: DOUBLE became DBF type F (float). A shapefile has no double, so the geodatabase type the contract asked for does not exist in the format that was written instead.
- `elevation_m`: DOUBLE became DBF type F (float). A shapefile has no double, so the geodatabase type the contract asked for does not exist in the format that was written instead.
- `is_enchanted`: the contract substituted SHORT for a boolean because an Enterprise Geodatabase has no boolean type - and the shapefile wrote DBF type L, which is a boolean. The format that cannot be the target represents this column better than the target can.

## The documentation conflict, unresolved

The guide says shapefile-only without arcpy. The current API reference documents an
`ARCGIS_IO_ENGINE` variable with options `'shapefile'`, `'gdal'` and `'arcpy'`, and says
"the first available library in the environment will be used". Neither page says what
the GDAL engine can write.

<https://developers.arcgis.com/python/latest/api-reference/arcgis.features.toc.html>

Recorded as an open conflict rather than settled by guessing. The environment table
above says which libraries were present, so this report answers for this machine and
claims nothing beyond it.
