#!/usr/bin/env python3
"""Real, full-scale state/county distribution ingest, all 35,326 species.

Source: the NRCS ArcGIS REST service at apps.geo.fpac.usda.gov/nrcs-geodata
(land_use_land_cover/plants/MapServer), found by watching live network
traffic on a real USDA plant-profile page -- same technique that found
PlantCharacteristics in Phase 1.5. Its own service description says it's
"intended for public use." Layer 4 (States and Provinces) and Layer 6
(Counties) both return real per-species occurrence rows when queried with
where=plant_master_id=<id> -- confirmed the only query shape that actually
works; bulk pagination (resultRecordCount/resultOffset) returns 400 despite
being advertised in the service's own metadata, so this goes per-species,
same resumable/cached pattern as every other USDA source here.

Validated first on a real 150-species prototype (data/prototype_distribution.py,
2026-11-02) before this script was written. Two real findings from that
prototype are handled here, not re-discovered the hard way:

1. County-level rows have real duplicates baked into the source service
   itself (28.8% of raw rows in the prototype sample) -- deduped here with
   SELECT DISTINCT at insert time, and the live schema's own UNIQUE index
   (species_symbol, level, subdivision_name) is a second, structural
   backstop against this ever silently reappearing.
2. plant_nativity_id is a bare numeric code with no inline lookup table.
   Cross-checked against species.native_status on 26,913 real prototype
   rows: code 5 = native (99.99% agreement), codes 3 and 7 both read as
   introduced (>99.5% agreement each) -- the exact difference between 3 and
   7 isn't resolved, both map to 'introduced' here. Any other code is
   stored as None (unknown) rather than guessed.

Resumable: each species' raw state+county response is cached to
data/cache_distribution/<symbol>.json before touching the database (the
150-species prototype already populated some of these -- this run reuses
them, same as every other cached ingest in this project).
"""
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

HERE = Path(__file__).parent
CACHE_PROFILES = HERE / "cache"
CACHE_DIST = HERE / "cache_distribution"
DB_PATH = HERE / "baneward.db"
API = "https://apps.geo.fpac.usda.gov/nrcs-geodata/rest/services/land_use_land_cover/plants/MapServer"
HEADERS = {"User-Agent": "Baneward-ingest/0.1 (+github.com/frankprobst5-stack/Baneward; research/offline-reference use)"}
WORKERS = 5  # kept conservative -- this service has only been proven at a 150-species, 38-second burst so far
RETRIES = 3

# Real, tested crosswalk from the 150-species prototype (26,913 rows).
# Code 5 -> native (22,882/22,882 real agreement with known L48 status).
# Codes 3 and 7 -> introduced (2,671/2,676 and 1,233/1,233 real agreement).
# Any other code: stored as None (unknown), not guessed.
NATIVITY_CROSSWALK = {"5": "native", "3": "introduced", "7": "introduced"}


def all_targets():
    targets = []
    for f in CACHE_PROFILES.glob("*.json"):
        d = json.loads(f.read_text())
        profile = d.get("profile") or {}
        if profile.get("Id"):
            targets.append((f.stem, profile["Id"]))
    return targets


def fetch_json(url, retries=RETRIES):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {url}: {last_err}")


def fetch_one(symbol, plant_id):
    cache_file = CACHE_DIST / f"{symbol}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    result = {"states": [], "counties": [], "errors": []}
    for level, layer in (("states", 4), ("counties", 6)):
        url = (
            f"{API}/{layer}/query?where=plant_master_id%3D{plant_id}"
            "&outFields=country_subdivision_name,plant_nativity_id"
            "&returnGeometry=false&f=json"
        )
        try:
            data = fetch_json(url)
            if "error" in data:
                result["errors"].append(f"{level}: {data['error']}")
            else:
                result[level] = [
                    {
                        "name": feat["attributes"]["country_subdivision_name"],
                        "nativity_code": feat["attributes"]["plant_nativity_id"],
                    }
                    for feat in data.get("features", [])
                ]
        except Exception as e:  # noqa: BLE001
            result["errors"].append(f"{level}: {e}")

    cache_file.write_text(json.dumps(result))
    return result


def main():
    CACHE_DIST.mkdir(exist_ok=True)
    targets = all_targets()
    total = len(targets)
    print(f"Fetching real distribution data for all {total} species...")

    results = {}
    done = 0
    hard_errors = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, sym, pid): sym for sym, pid in targets}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                r = fut.result()
                results[sym] = r
                if r["errors"]:
                    hard_errors += 1
                    print(f"!! {sym}: {r['errors']}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"!! {sym}: hard failure: {e}", file=sys.stderr)
                results[sym] = {"states": [], "counties": [], "errors": [str(e)]}
                hard_errors += 1
            done += 1
            if done % 1000 == 0 or done == total:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed else 0
                remaining = (total - done) / rate if rate else 0
                print(f"{done}/{total}  ({elapsed:.0f}s elapsed, ~{remaining/60:.0f}m remaining)")
    elapsed_total = time.time() - start

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM distribution")  # idempotent re-run
    level_singular = {"states": "state", "counties": "county"}
    unknown_codes = set()
    rows_inserted = 0
    rows_deduped = 0
    for sym, r in results.items():
        for level in ("states", "counties"):
            seen = set()
            for row in r[level]:
                name = row["name"]
                if name in seen:
                    rows_deduped += 1
                    continue
                seen.add(name)
                code = row["nativity_code"]
                status = NATIVITY_CROSSWALK.get(code)
                if status is None and code is not None:
                    unknown_codes.add(code)
                conn.execute(
                    "INSERT INTO distribution (species_symbol, level, subdivision_name, nativity_status) VALUES (?,?,?,?)",
                    (sym, level_singular[level], name, status),
                )
                rows_inserted += 1
    conn.commit()

    n_species = len(results)
    n_zero_state = sum(1 for r in results.values() if not r["states"])
    n_zero_county = sum(1 for r in results.values() if not r["counties"])

    print("\n=== Real final results ===")
    print(f"Species: {n_species}, hard errors: {hard_errors}")
    print(f"Species with zero state rows: {n_zero_state} ({100*n_zero_state/n_species:.1f}%)")
    print(f"Species with zero county rows: {n_zero_county} ({100*n_zero_county/n_species:.1f}%)")
    print(f"Rows inserted (deduped): {rows_inserted}")
    print(f"Duplicate rows dropped at insert: {rows_deduped}")
    if unknown_codes:
        print(f"Real unknown nativity codes seen, not in the crosswalk (stored as NULL): {sorted(unknown_codes)}")
    print(f"Elapsed: {elapsed_total:.0f}s for {n_species} species ({WORKERS} workers)")
    print(f"\nDatabase: {DB_PATH}")


if __name__ == "__main__":
    main()
