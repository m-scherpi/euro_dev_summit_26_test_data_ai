# Verification: `agsdb.sde.nrw_points`

Feature class read back from the Enterprise Geodatabase via `build\egdb.sde` and compared
against `output\nrw_points_schema.json` and `..\csv_data\output\nrw_points.csv`.

Verification depth: **plausible is enough** (agreed up front, CLAUDE.md section 12).
Rows matched on `id`.

**10 of 10 checks passed, all green.**

| Check | Result | Detail |
|---|---|---|
| Feature count matches the source | PASS | 100 features, 100 rows in `nrw_points.csv` |
| Field types and lengths match the contract | PASS | all 10 declared fields agree |
| No unexpected fields | PASS | geodatabase-managed: objectid, shape |
| Spatial reference is the one the contract names | PASS | EPSG:4326 (`GCS_WGS_1984`), contract says EPSG:4326. A wrong code here does not error at write time. |
| Extent equals the source's measured extent | PASS | x 5.88000..9.44000, y 50.32500..52.53000; largest disagreement with the source 5.51e-14 degrees |
| Transposed bounding box matches nothing | PASS | 0 of 100 features inside x 50.325..52.530, y 5.880..9.440. This is the only check that sees an axis swap here: both NRW coordinate ranges are valid latitudes, so the geodatabase accepts a swapped load without complaint and puts every point in the Somali Sea at a perfectly valid coordinate. |
| Every geometry equals its source coordinate pair | PASS | 100 features matched on `id`; worst disagreement 8.53e-14 degrees (`16`). Nothing is projected or rounded in this pipeline, so the comparison is exact rather than tolerant. |
| The second coordinate pair survived as attributes | PASS | x_3857, y_3857 agree with the source in all 100 features |
| Boolean columns are SHORT, and the table cannot say so | INFO | `is_enchanted` held true/false in the source and hold 1/0 here, because an Enterprise Geodatabase has no boolean type. The attribute table shows a number with no way to indicate what it was. |
| Field name limit | INFO | the longest declared field name is 13 characters against the geodatabase's limit of 31. PostgreSQL itself allows 63, so a name between 32 and 63 would be stored by the database and unaddressable through ArcGIS. |
