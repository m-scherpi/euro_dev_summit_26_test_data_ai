#!/usr/bin/env python3
"""Publish the Munster rent census to an ArcGIS Enterprise Portal.

This script is a transcription of documents somebody already read. Every
decision it carries out was made offline by `build_portal_items.py` and is
sitting in `output/` as reviewable JSON: the schema declaration, the
service-level renderer, the whole web map. What is left here is four calls, a
substitution and a report.

Five stages, cumulative, each leaving a working deliverable:

    csv       -> a CSV item in the portal
    publish   -> a hosted feature layer, published with OUR publishParameters
                 (and the portal's own guess dumped next to them)
    layerdef  -> the class-breaks renderer pushed onto the service itself
    webmap    -> a Web Map with five operational layers on that one service
    all       -> all of the above

Two inversions of findings this repository made elsewhere, both deliberate:

* `opensearch` publishes a web feature layer that **references** registered
  data and copies nothing. This copies all data - the rows end up in the
  ArcGIS Data Store.
* `egdb_import` refused `GIS.content.import_data()` *because* it copies rows
  out of a database into a hosted layer. Here that copy is the deliverable.
  Same measurement, opposite verdict.

`import_data()` is still not used, and now for three reasons that are about the
method rather than the goal: it takes a DataFrame, it offers no control over
field types, and its documentation states a 1,000-row cap. `Item.publish()`
with explicit `publishParameters` is the route that lets the schema be
declared. `overwrite=True` is not used either - it is documented as
incompatible with `publish_parameters`, so overwriting would silently mean
giving up the declaration.

**`--dry-run` needs no portal and no `arcgis`.** The library is imported lazily,
inside the function that connects, so the rehearsal runs under a bare
`python3`: token substitution, the zero-unresolved assertion, JSON validity,
and a coercion of every row against every declared field type. A dry run that
only prints the calls it would make is worth much less - `egdb_import`'s row
rehearsal caught three planted defects with no database in sight.

Requires `arcgis` 2.4.1.1 for the real run - see `requirements.txt`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from census import (  # noqa: E402  (needs the path above)
    DEFAULT_SERVICE_NAME,
    FIELD_TYPES,
    ITEM_TAG,
    TOKEN_ITEM_ID,
    TOKEN_MARKER,
    TOKEN_SERVICE_URL,
)

PASSWORD_ENV = "PORTAL_PASSWORD"

# Every log line that would otherwise carry the password carries this instead.
# A constant rather than a `.replace()` at print time: the value never enters a
# formatted string in the first place.
REDACTED = f"<{PASSWORD_ENV}>"

STAGES = ("csv", "publish", "layerdef", "webmap")

# What `--recreate` deletes, in this order. The order is not cosmetic: the
# feature service holds a `Service2Data` relationship back to the CSV item, and
# the publish path reads it. Deleting the CSV first can leave that relationship
# dangling, so the dependants go first and the source last.
DELETE_ORDER = ("Web Map", "Feature Service", "CSV")

# `content.search` defaults to `max_items=10`, which is a silent truncation
# rather than an error - a demo run three times leaves more than ten items and
# `--recreate` would then quietly leave some behind.
SEARCH_MAX_ITEMS = 200

# Values used by --dry-run in place of the ids that do not exist yet. Obviously
# fake on purpose: a rehearsal that substitutes something plausible invites the
# substituted body to be mistaken for a real one.
DRY_RUN_SERVICE_URL = (
    "https://portal.invalid/server/rest/services/Hosted/DRY_RUN/FeatureServer"
)
DRY_RUN_ITEM_ID = "0" * 32

TOKEN_PATTERN = re.compile(r"\{\{[^}]*\}\}")


class PublishError(Exception):
    """Something the publisher refuses to do."""


# ---------------------------------------------------------------------------
# Token substitution
# ---------------------------------------------------------------------------


def substitute(body: dict, service_url: str, item_id: str) -> dict:
    """Replace the placeholders in a payload and prove none survived.

    The assertion is the point of the whole placeholder mechanism. An
    unsubstituted `{{FEATURE_SERVICE_URL}}` produces a web map that **loads**:
    the portal accepts the item, the map viewer opens it, the frame draws, the
    legend lists five layers and not one feature appears. There is no error
    anywhere - CLAUDE.md section 4's rule that the loud error is the harmless
    one, one level up from a coordinate.

    The check greps for the marker rather than for the known token names, so a
    typo in a template - `{{FEATURE_SERVICE_UR}}` - fails too. A whitelist
    would pass it.
    """
    text = json.dumps(body)
    text = text.replace(TOKEN_SERVICE_URL, service_url).replace(TOKEN_ITEM_ID, item_id)
    leftover = sorted(set(TOKEN_PATTERN.findall(text)))
    if leftover:
        raise PublishError(
            f"{len(leftover)} unresolved placeholder(s) after substitution: "
            f"{', '.join(leftover)}. Nothing was uploaded. An unsubstituted token yields "
            f"an item that loads, renders its frame and shows no data, so this aborts "
            f"instead of warning."
        )
    return json.loads(text)


# ---------------------------------------------------------------------------
# Offline rehearsal
# ---------------------------------------------------------------------------


COERCERS = {
    "esriFieldTypeInteger": int,
    "esriFieldTypeDouble": float,
}


def rehearse_rows(csv_path: Path, max_reported: int = 10) -> dict:
    """Coerce every value of every row against its declared field type.

    This is the half of the dry run that does real work. The portal will apply
    these types on its side, row by row, and a type failure there arrives as an
    error about a row - hundreds of rows in, with the schema nowhere in the
    message. Doing it here means the answer arrives before anything is
    uploaded.

    Copied in spirit from `egdb_import`, where the equivalent rehearsal caught
    three planted defects with no database in sight, and where an earlier
    version found a real bug: 1,343 single-space values that one side counted
    as present and the other as absent.
    """
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    problems: list[str] = []
    if fieldnames != list(FIELD_TYPES):
        problems.append(
            f"header is {fieldnames}, the declaration in census.py is {list(FIELD_TYPES)}"
        )

    text_max: dict[str, int] = {}
    for number, row in enumerate(rows, start=2):
        for column, spec in FIELD_TYPES.items():
            raw = row.get(column)
            if raw is None:
                problems.append(f"line {number}: column {column!r} is absent")
                continue
            esri_type = str(spec["type"])
            if esri_type == "esriFieldTypeString":
                length = int(spec["length"])  # type: ignore[arg-type]
                text_max[column] = max(text_max.get(column, 0), len(raw))
                if len(raw) > length:
                    problems.append(
                        f"line {number}: {column}={raw!r} is {len(raw)} characters, "
                        f"declared TEXT({length})"
                    )
                continue
            try:
                COERCERS[esri_type](raw)
            except (TypeError, ValueError):
                problems.append(
                    f"line {number}: {column}={raw!r} is not a valid {esri_type}"
                )

    return {
        "rows": len(rows),
        "values": len(rows) * len(FIELD_TYPES),
        "text_max": text_max,
        "problems": problems[:max_reported],
        "problem_count": len(problems),
    }


def render_plan(
    args: argparse.Namespace,
    items: dict[str, dict],
    rehearsal: dict,
    substituted: dict[str, Path],
) -> str:
    """The dry run's written plan: what would happen, in order, and what was proved."""
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    publish_parameters = items["publish_parameters"]
    webmap = items["webmap"]
    renderers = [
        layer["layerDefinition"]["drawingInfo"]["renderer"]["type"]
        for layer in webmap["operationalLayers"]
    ]
    urls = {layer["url"] for layer in webmap["operationalLayers"]}

    lines = [
        "# Publish plan (dry run) - Munster rent census",
        "",
        f"- Rehearsed: {now}",
        f"- CSV: `{args.csv}`",
        f"- Payloads: `{args.items_dir}`",
        f"- Service name: `{publish_parameters['name']}`",
        f"- Stage requested: `{args.stage}`",
        f"- Sharing: `{args.share}`",
        "",
        "**No portal was contacted and `arcgis` was never imported.** This rehearsal runs",
        "under a bare `python3`. Everything below is either a call that *would* be made or",
        "a claim that was actually checked here; the two are labelled.",
        "",
        "## What would happen",
        "",
        "| # | Stage | Call | Effect |",
        "|---|---|---|---|",
        "| 1 | `csv` | `gis.content.add({'type': 'CSV', ...}, data=csv)` | the CSV becomes "
        "a portal item |",
        "| 2 | `publish` | `gis.content.analyze(item=..., file_type='csv', "
        "location_type='coordinates')` | the portal's **guessed** publishParameters are "
        "dumped to `output/analyze_publish_parameters.json` and **not** used |",
        "| 3 | `publish` | `csv_item.publish(publish_parameters=<ours>, file_type='csv')` | "
        "a hosted feature layer with the declared schema |",
        "| 4 | `layerdef` | `layer.manager.update_definition(<drawingInfo>)` | the "
        "class-breaks renderer lands on the service itself |",
        "| 4b | `layerdef` | `layer.manager.update_definition({'fields': [...]})`, only "
        "with `--retrofit-field-lengths` | an experiment: the portal stored every "
        "declared TEXT column as TEXT(8000), and Esri does not document whether "
        "`length` is updatable afterwards. The answer goes into the run record |",
        "| 5 | `webmap` | `gis.content.add({'type': 'Web Map', 'text': ...})` | five "
        "operational layers on one service |",
        "",
        "Not used, and each for a documented reason: `import_data()` (DataFrame only, no",
        "field-type control, documented 1,000-row cap) and `publish(overwrite=True)`",
        "(documented as incompatible with `publish_parameters`, so overwriting would mean",
        "silently giving up the declaration).",
        "",
        "## What was actually checked",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Payload JSON parses | PASS ({len(items)} documents) |",
        f"| Placeholders substituted, none left | PASS (`{TOKEN_SERVICE_URL}`, "
        f"`{TOKEN_ITEM_ID}`) |",
        f"| Rows coerced against the declared field types | "
        f"{'PASS' if not rehearsal['problem_count'] else 'FAIL'} "
        f"({rehearsal['values']:,} values in {rehearsal['rows']:,} rows, "
        f"{rehearsal['problem_count']} problem(s)) |",
        f"| Web map carries four renderer types | "
        f"{'PASS' if len(set(renderers)) == 4 else 'FAIL'} ({', '.join(renderers)}) |",
        f"| All operational layers on one service URL | "
        f"{'PASS' if len(urls) == 1 else 'FAIL'} ({len(urls)} distinct URL(s)) |",
        "",
    ]
    if rehearsal["problems"]:
        lines += ["### Row problems", ""]
        lines += [f"- {p}" for p in rehearsal["problems"]]
        if rehearsal["problem_count"] > len(rehearsal["problems"]):
            lines.append(
                f"- _... and {rehearsal['problem_count'] - len(rehearsal['problems'])} more_"
            )
        lines.append("")

    lines += [
        "## Declared schema",
        "",
        "| Field | Declared type | Length |",
        "|---|---|---|",
    ]
    for field in publish_parameters["layerInfo"]["fields"]:
        lines.append(
            f"| `{field['name']}` | {field['type']} | {field.get('length', '-')} |"
        )
    lines += [
        "",
        "`columnNames` is omitted because `layerInfo.fields` overrides it. The portal's own",
        "guess is fetched in stage 2 and committed next to this declaration; the diff",
        "between the two is the central measurement of this use case.",
        "",
        "## Substituted bodies",
        "",
        "Written to `build/` and never to `output/`: they carry ids that do not exist yet",
        "and would change on every run, which is exactly what `output/` may not contain.",
        "",
    ]
    lines += [f"- `{path}`" for path in substituted.values()]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Portal
# ---------------------------------------------------------------------------


def connect(args: argparse.Namespace, password: str):
    """Open the portal connection. The only place `arcgis` is imported.

    **A private CA reaches this client through `GIS(ca_bundles=...)`, and only
    through it.** The first version of this function set `REQUESTS_CA_BUNDLE`
    before the import and said in this docstring that the order of those two
    lines was what mattered. That was wrong, and the correction is worth
    keeping visible: `arcgis` 2.4.1.1 mounts an `EsriTrustStoreAdapter` whose
    `init_poolmanager` hands urllib3 its **own** `ssl.SSLContext` - a
    `truststore.SSLContext` loaded with `certifi.where()` - and a connection
    built from an explicit context never consults requests' `verify`, so the
    environment variable is read by nothing. Measured in the same interpreter:
    `requests.get(portal_url)` with `REQUESTS_CA_BUNDLE` set returns **200**
    and `GIS(portal_url)` under the identical environment raises
    `CERTIFICATE_VERIFY_FAILED`. One process, one variable, two answers.

    `ca_bundles` is documented in the class's own docstring in the wheel -
    *"Users can pass verify_cert a path to a CA_BUNDLE file or directory with
    certificates of trusted CAs as well. This will use these certificates over
    the system's certificates."* - which is the `arcgis.map` lesson again: ask
    the wheel, not the notes. The variable is still exported, because plain
    `requests` calls elsewhere in a session do honour it, but it is the belt
    and `ca_bundles` is the trousers.

    CLAUDE.md section 4 on trust stores applies with full force here and is
    worth restating: "the consumer" is a list, and this is a fifth entry on it.
    A private CA that satisfies this Python client says nothing about ArcGIS
    Pro (Current User store), an ArcGIS Server service (Local Computer store)
    or that server's JVM (its own `cacerts`) - and, as this function now
    records, satisfying `requests` in a process says nothing about satisfying
    `arcgis` in that same process.
    """
    ca_bundle = None
    if args.ca_cert:
        ca_path = Path(args.ca_cert).resolve()
        if not ca_path.is_file():
            raise PublishError(f"--ca-cert not found: {ca_path}")
        ca_bundle = str(ca_path)
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle

    try:
        from arcgis.gis import GIS
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise PublishError(
            f"arcgis is not importable ({exc}). Install it into a local venv with "
            f"`python3 -m venv build/venv_api && build/venv_api/bin/pip install -r "
            f"requirements.txt`, and run this script with that interpreter. Or use "
            f"--dry-run, which needs neither."
        ) from None

    print(f"connecting to {args.portal} as {args.user} (password: {REDACTED})")
    kwargs = {"ca_bundles": ca_bundle} if ca_bundle else {}
    return GIS(
        args.portal,
        username=args.user,
        password=password,
        verify_cert=not args.no_verify_cert,
        **kwargs,
    )


def find_own_items(gis, service_name: str) -> list:
    """Every item this use case created, and only those.

    `max_items` is explicit. The default is 10, and a silent truncation here
    would leave items behind on the third run of a demo and then fail the
    service-name check for a reason that looks unrelated.
    """
    query = f'tags:"{ITEM_TAG}" AND owner:{gis.users.me.username}'
    found = gis.content.search(query=query, max_items=SEARCH_MAX_ITEMS)
    if len(found) >= SEARCH_MAX_ITEMS:
        print(
            f"warning: the search returned {len(found)} items, which is the requested "
            f"maximum - there may be more. Raise SEARCH_MAX_ITEMS."
        )
    # No further filtering: the tag is this use case's own and nothing else
    # carries it, so narrowing by title as well would only be a second chance to
    # get the predicate wrong - and an item this use case created under a
    # different --service-name is still one it has to clean up.
    return list(found)


def recreate(gis, service_name: str) -> list[dict]:
    """Delete this use case's previous items, dependants first.

    Every deletion is preceded by `Item.delete(dry_run=True)`, whose answer is
    logged. That is the API asking the portal whether anything else depends on
    the item, and a blocked deletion is worth a line in the record rather than
    an exception in the middle of a demo.

    Note what this cannot promise. `permanent=True` is documented as ArcGIS
    Online only, so on Enterprise a deleted item may go to a recycle bin and
    **keep its service name**. `is_service_name_available` is therefore asked
    separately afterwards, and it can legitimately say no right after a
    successful delete.
    """
    record: list[dict] = []
    items = find_own_items(gis, service_name)
    by_type: dict[str, list] = {}
    for item in items:
        by_type.setdefault(item.type, []).append(item)

    for item_type in DELETE_ORDER:
        for item in by_type.get(item_type, []):
            entry = {"id": item.id, "type": item.type, "title": item.title}
            try:
                probe = item.delete(dry_run=True)
                entry["dry_run"] = probe
                blockers = (probe or {}).get("dependencies") if isinstance(probe, dict) else None
                if blockers:
                    entry["blocked_by"] = blockers
                    print(f"  {item.type} {item.id}: blocked by {blockers}")
            except Exception as exc:  # pragma: no cover - portal dependent
                entry["dry_run_error"] = str(exc)
            try:
                entry["deleted"] = bool(item.delete())
            except Exception as exc:  # pragma: no cover - portal dependent
                entry["deleted"] = False
                entry["error"] = str(exc)
            print(f"  deleted {entry['type']} {entry['id']} ({entry['title']}): "
                  f"{entry['deleted']}")
            record.append(entry)

    leftover = [i for i in items if i.type not in DELETE_ORDER]
    for item in leftover:
        print(f"  note: leaving {item.type} {item.id} ({item.title}) - not in DELETE_ORDER")
    return record


def apply_sharing(item, level: str) -> None:
    """Set the item's sharing level.

    `item.sharing.sharing_level` rather than the deprecated `Item.share()`.
    Default **private**: an item shared with the organisation by accident is a
    decision somebody else has to undo, and this repository's own rule is that
    outward-facing actions get confirmed rather than defaulted.
    """
    item.sharing.sharing_level = level


def publish(args: argparse.Namespace, password: str, items: dict) -> dict:
    """Run the requested stages against the portal, and record what happened."""
    stages = STAGES if args.stage == "all" else STAGES[: STAGES.index(args.stage) + 1]
    service_name = items["publish_parameters"]["name"]
    gis = connect(args, password)

    record: dict = {
        "portal": args.portal,
        "user": args.user,
        "password": REDACTED,
        "service_name": service_name,
        "stages_requested": list(stages),
        "started": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tag": ITEM_TAG,
        "items": {},
    }

    if args.recreate:
        print("recreate: deleting this use case's previous items")
        record["recreated"] = recreate(gis, service_name)

    available = gis.content.is_service_name_available(service_name, "featureService")
    record["service_name_available"] = bool(available)
    if not available:
        raise PublishError(
            f"the service name {service_name!r} is not available on this portal. Either "
            f"an earlier run's service still exists (pass --recreate), or it was deleted "
            f"into a recycle bin that still holds the name - `permanent=True` is "
            f"documented as ArcGIS Online only, so on Enterprise a deleted item can keep "
            f"its name. Pass --service-name to publish under a different one."
        )

    common = {
        "tags": [ITEM_TAG, "devsummit", "test-data", "fictitious"],
        "snippet": "Fictitious rent-price census for Munster - generated test data.",
        "description": items["publish_parameters"]["description"],
        "accessInformation": "Generated test data. Nothing in this item is real.",
        "licenseInfo": (
            "CC BY 4.0, as part of the euro_dev_summit_26_test_data_ai repository."
        ),
    }

    # 1. The CSV item.
    print(f"stage csv: adding {args.csv}")
    csv_item = gis.content.add(
        {**common, "type": "CSV", "title": f"{service_name} (source CSV)"},
        data=str(args.csv),
    )
    apply_sharing(csv_item, args.share)
    record["items"]["csv"] = {"id": csv_item.id, "type": csv_item.type,
                              "title": csv_item.title}
    print(f"  CSV item {csv_item.id}")

    if "publish" in stages:
        # 2. Ask the portal what it would have guessed - and do not use it.
        print("stage publish: asking the portal for its own publishParameters")
        analysis = gis.content.analyze(
            item=csv_item, file_type="csv", location_type="coordinates"
        )
        guessed = (analysis or {}).get("publishParameters", analysis)
        guess_path = args.items_dir / "analyze_publish_parameters.json"
        with guess_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(guessed, indent=2, sort_keys=False) + "\n")
        record["analyze_publish_parameters"] = str(guess_path)
        print(f"  wrote {guess_path} - the portal's guess, kept for the diff, not used")

        # 3. Publish with ours.
        print("  publishing with our declared publishParameters")
        layer_item = csv_item.publish(
            publish_parameters=items["publish_parameters"], file_type="csv"
        )
        apply_sharing(layer_item, args.share)
        record["items"]["feature_layer"] = {
            "id": layer_item.id, "type": layer_item.type,
            "title": layer_item.title, "url": layer_item.url,
        }
        print(f"  feature layer item {layer_item.id} -> {layer_item.url}")

        if "layerdef" in stages:
            # 4. The service-level renderer.
            print("stage layerdef: pushing the class-breaks renderer onto the service")
            layer = layer_item.layers[0]
            body = items["layer_definition"]["update_definition"]
            result = layer.manager.update_definition(body)
            record["update_definition"] = result
            print(f"  update_definition: {result}")

            # 4b. An experiment, not a fix. The portal accepted the declared
            # `layerInfo.fields` at publish time and stored every TEXT column as
            # TEXT(8000) anyway - the types survived, the lengths did not, and
            # nothing said so. Esri's updateDefinition reference says only
            # "When updating field properties, note that not all of these
            # properties may be updated" and does not say which, so the
            # instance is asked rather than the document. Both outcomes are a
            # result: the raw response goes into the run record either way, and
            # `verify_portal.py` reads the stored lengths back out of the
            # service rather than believing this call's return value.
            if args.retrofit_field_lengths:
                print("stage layerdef: retrofitting the declared TEXT lengths (experiment)")
                field_body = items["layer_definition"].get("field_length_update")
                if not field_body:
                    raise PublishError(
                        "output/layer_definition.json carries no field_length_update "
                        "body. Rebuild it with build_portal_items.py."
                    )
                try:
                    retrofit = layer.manager.update_definition(field_body)
                    record["field_length_update"] = {
                        "requested": field_body, "response": retrofit, "raised": None,
                    }
                    print(f"  field length update: {retrofit}")
                except Exception as exc:  # noqa: BLE001 - the refusal IS the measurement
                    record["field_length_update"] = {
                        "requested": field_body, "response": None, "raised": str(exc),
                    }
                    print(f"  field length update refused: {exc}")

        if "webmap" in stages:
            # 5. The web map.
            print("stage webmap: substituting placeholders and adding the Web Map")
            webmap = substitute(items["webmap"], layer_item.url, layer_item.id)
            build_dir = Path("build")
            build_dir.mkdir(exist_ok=True)
            substituted_path = build_dir / "webmap_substituted.json"
            substituted_path.write_text(
                json.dumps(webmap, indent=2) + "\n", encoding="utf-8", newline="\n"
            )
            # The item extent is DEGREES and the map's viewpoint is METRES. An
            # ArcGIS item's `extent` property is documented as decimal degrees
            # (WGS84); this map's spatial reference is EPSG:3857 because
            # targetSR defaults to 102100. Handing the viewpoint's metres to the
            # item property gives an item whose extent is nonsense and whose map
            # draws correctly, so nothing anywhere complains - the
            # Gulf-of-Guinea failure from `egdb_import`, one level up.
            item_extent = webmap["_item"]["extent_4326"]
            # Underscore keys are this repository's notes to a reader of
            # output/webmap.json, not part of the web map. Strip them, or the
            # commentary ends up inside the live item.
            body = {k: v for k, v in webmap.items() if not k.startswith("_")}
            webmap_item = gis.content.add(
                {
                    **common,
                    "type": "Web Map",
                    "title": "Munster rent census (five layers, four renderer types)",
                    "typeKeywords": ["Web Map", "Map", "Online Map", "ArcGIS Online"],
                    "text": json.dumps(body),
                    "extent": item_extent,
                }
            )
            apply_sharing(webmap_item, args.share)
            record["items"]["webmap"] = {
                "id": webmap_item.id, "type": webmap_item.type,
                "title": webmap_item.title,
            }
            print(f"  web map item {webmap_item.id}")
            print(f"  open it at {args.portal.rstrip('/')}/home/webmap/"
                  f"viewer.html?webmap={webmap_item.id}")

    record["finished"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record["sharing_level"] = args.share
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_items(items_dir: Path) -> dict:
    """Read the three offline payloads."""
    names = {
        "publish_parameters": "publish_parameters.json",
        "layer_definition": "layer_definition.json",
        "webmap": "webmap.json",
    }
    loaded = {}
    for key, filename in names.items():
        path = items_dir / filename
        if not path.is_file():
            raise PublishError(
                f"{path} not found. Run build_portal_items.py first - this script "
                f"transports its payloads and does not invent them."
            )
        loaded[key] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="publish_to_portal.py",
        description=(
            "Publish the Munster rent census to an ArcGIS Enterprise Portal: the CSV as "
            "an item, a hosted feature layer with a declared schema, the class-breaks "
            "renderer on the service, and a Web Map with five operational layers on that "
            "one service. --dry-run rehearses everything reachable offline and needs "
            "neither a portal nor the arcgis library."
        ),
        epilog=(
            "Examples:\n"
            "  # Rehearse offline - no portal, no arcgis, no credentials\n"
            "  python3 scripts/publish_to_portal.py --dry-run \\\n"
            "      --csv output/muenster_rent_census.csv --items-dir output/ \\\n"
            "      --plan build/publish_plan.md\n\n"
            "  # The real run\n"
            "  export PORTAL_PASSWORD=...\n"
            "  build/venv_api/bin/python scripts/publish_to_portal.py \\\n"
            "      --portal https://portal.example.com/portal --user devsummit \\\n"
            "      --csv output/muenster_rent_census.csv --items-dir output/ \\\n"
            "      --stage all --recreate --run-record build/portal_run.json\n\n"
            f"The password comes from ${PASSWORD_ENV} or --password. It has no default,\n"
            "is committed nowhere, and appears in no log line - every script prints\n"
            f"{REDACTED} instead. See input/portal_connection.example.json for why the\n"
            "throwaway-credential exception opensearch takes is deliberately not taken\n"
            "here.\n\n"
            "A literal 'localhost' in --portal is resolved by the federated server on\n"
            "its own machine, not on yours. Use the host name the certificate names."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--csv", type=Path, default=Path("output/muenster_rent_census.csv"),
        metavar="CSV", help="the generated census CSV to upload (default: %(default)s)",
    )
    parser.add_argument(
        "--items-dir", type=Path, default=Path("output"), metavar="DIR",
        help="directory holding the three payloads from build_portal_items.py "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--stage", choices=(*STAGES, "all"), default="all",
        help="how far to go; the stages are cumulative (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="rehearse offline and write a plan: token substitution, the "
        "zero-unresolved assertion, JSON validity and a coercion of every row against "
        "every declared field type. Contacts no portal and does not import arcgis",
    )
    parser.add_argument(
        "--plan", type=Path, default=None, metavar="MD",
        help="where --dry-run writes its plan. No default (CLAUDE.md section 4); "
        "without it the plan goes to stdout",
    )
    parser.add_argument(
        "--portal", default=None, metavar="URL",
        help="portal URL, e.g. https://portal.example.com/portal. Required unless "
        "--dry-run",
    )
    parser.add_argument(
        "--user", default=None, metavar="NAME",
        help="portal user. Required unless --dry-run",
    )
    parser.add_argument(
        "--password", default=None, metavar="SECRET",
        help=f"portal password; defaults to ${PASSWORD_ENV}. Never stored in this "
        f"repository and never printed",
    )
    parser.add_argument(
        "--service-name", default=None, metavar="NAME",
        help=f"override the hosted service name from publish_parameters.json "
        f"(built as {DEFAULT_SERVICE_NAME!r})",
    )
    parser.add_argument(
        "--share", choices=("PRIVATE", "ORGANIZATION", "EVERYONE"), default="PRIVATE",
        help="sharing level for every item created (default: %(default)s). Private by "
        "default because widening access is somebody else's problem to undo",
    )
    parser.add_argument(
        "--recreate", action="store_true",
        help="delete this use case's previous items first, dependants before sources, "
        "each preceded by a logged Item.delete(dry_run=True)",
    )
    parser.add_argument(
        "--retrofit-field-lengths", action="store_true",
        help="after the renderer, POST the declared TEXT lengths to the service and "
        "record what it answers. An experiment, not a fix: the portal stores every "
        "declared TEXT column as TEXT(8000) at publish time and Esri does not "
        "document whether length is updatable afterwards",
    )
    parser.add_argument(
        "--ca-cert", default=None, metavar="PEM",
        help="CA bundle for a private certificate authority; sets REQUESTS_CA_BUNDLE "
        "before arcgis is imported, which is the only order that works",
    )
    parser.add_argument(
        "--no-verify-cert", action="store_true",
        help="disable TLS verification (GIS(verify_cert=False)). A debugging aid, not a "
        "fix - prefer --ca-cert",
    )
    parser.add_argument(
        "--run-record", type=Path, default=None, metavar="JSON",
        help="write the item ids and stage results here, for verify_portal.py to read. "
        "Belongs in build/: item ids change on every run and output/ must stay "
        "regenerable from input/",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.csv.is_file():
        print(f"error: CSV not found: {args.csv}", file=sys.stderr)
        return 1

    try:
        items = load_items(args.items_dir)
    except (PublishError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.service_name:
        items["publish_parameters"]["name"] = args.service_name
        items["publish_parameters"]["layerInfo"]["name"] = args.service_name

    if args.dry_run:
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)
        substituted_paths: dict[str, Path] = {}
        try:
            for key in ("webmap", "layer_definition", "publish_parameters"):
                body = substitute(items[key], DRY_RUN_SERVICE_URL, DRY_RUN_ITEM_ID)
                path = build_dir / f"{key}_substituted.json"
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(body, indent=2) + "\n")
                substituted_paths[key] = path
        except PublishError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        rehearsal = rehearse_rows(args.csv)
        plan = render_plan(args, items, rehearsal, substituted_paths)
        if args.plan is None:
            print(plan)
        else:
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            args.plan.write_text(plan + "\n", encoding="utf-8")

        renderers = [
            layer["layerDefinition"]["drawingInfo"]["renderer"]["type"]
            for layer in items["webmap"]["operationalLayers"]
        ]
        urls = {layer["url"] for layer in items["webmap"]["operationalLayers"]}
        print(
            f"dry run: {rehearsal['rows']:,} rows, {rehearsal['values']:,} values coerced "
            f"against {len(FIELD_TYPES)} declared field types | "
            f"problems: {rehearsal['problem_count']}"
        )
        print(
            f"renderers: {', '.join(renderers)} | distinct service URLs in the web map: "
            f"{len(urls)}"
        )
        print(
            "placeholders substituted and none left; substituted bodies in "
            + ", ".join(str(p) for p in substituted_paths.values())
        )
        if args.plan is not None:
            print(f"wrote {args.plan}")
        print("no portal was contacted and arcgis was never imported")
        return 1 if rehearsal["problem_count"] else 0

    missing = [name for name, value in (("--portal", args.portal), ("--user", args.user))
               if not value]
    if missing:
        print(
            f"error: {', '.join(missing)} required for a real run. Use --dry-run to "
            f"rehearse without a portal.",
            file=sys.stderr,
        )
        return 1

    password = args.password or os.environ.get(PASSWORD_ENV)
    if not password:
        print(
            f"error: no password. Set ${PASSWORD_ENV} or pass --password. It is "
            f"deliberately not read from any file in this repository - see "
            f"input/portal_connection.example.json.",
            file=sys.stderr,
        )
        return 1

    try:
        record = publish(args, password, items)
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.run_record is not None:
        args.run_record.parent.mkdir(parents=True, exist_ok=True)
        with args.run_record.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, indent=2, default=str) + "\n")
        print(f"wrote {args.run_record}")
    print(
        "items: "
        + ", ".join(f"{k}={v['id']}" for k, v in record["items"].items())
        + f" | shared: {record['sharing_level']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
