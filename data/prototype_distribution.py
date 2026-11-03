#!/usr/bin/env python3
"""Bounded prototype for real state/county-level distribution data.

Real source, verified live on 2026-11-02: the NRCS ArcGIS REST service at
apps.geo.fpac.usda.gov/nrcs-geodata/rest/services/land_use_land_cover/plants/
MapServer -- found by watching live network traffic on a real USDA plant
profile page, same technique that found PlantCharacteristics in Phase 1.5.
Its own service description says it's "intended for public use." Layer 4
("States and Provinces") and Layer 6 ("Counties") both return real
per-species occurrence rows (country_subdivision_name + a plant_nativity_id
code) when queried with where=plant_master_id=<id> -- the one query shape
confirmed to actually work; bulk pagination (resultRecordCount/resultOffset)
was tested and returns 400 despite being advertised in the service's own
metadata, so this has to go per-species, same resumable/cached pattern as
every other USDA source in this project.

This script does NOT touch the live app, its schema, or its running
database. It fetches a bounded ~150-species sample (a deliberately chosen
set of species this project already cares about, plus a random sample for
real throughput/coverage numbers), caches raw responses, writes them into a
new `distribution` table in a SEPARATE prototype database
(data/distribution_prototype.db), and prints real, measured stats -- same
"prove it on a small batch before scaling" discipline as build_phase0.py and
the 100-species iNaturalist prototype (Phase 1.9).
"""
import json
import random
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

HERE = Path(__file__).parent
CACHE_PROFILES = HERE / "cache"
CACHE_DIST = HERE / "cache_distribution"
MASTER_DB = HERE / "baneward.db"
PROTO_DB = HERE / "distribution_prototype.db"
API = "https://apps.geo.fpac.usda.gov/nrcs-geodata/rest/services/land_use_land_cover/plants/MapServer"
HEADERS = {"User-Agent": "Baneward-ingest/0.1 (+github.com/frankprobst5-stack/Baneward; research/offline-reference use)"}
WORKERS = 5  # conservative on purpose -- this NRCS service has never been load-tested by this project before
RETRIES = 3
SAMPLE_SIZE = 150

DELIBERATE_SYMBOLS = [
    "COMA2",   # poison hemlock
    "DACA6",   # Queen Anne's lace / wild carrot
    "CIMA2", "CIDO", "CIBU", "CIVI5",  # water hemlocks (4 species)
    "TORA2", "TORY",  # poison ivy (2 species)
    "TOPU2", "TODI",  # poison oak (2 species)
    "TYLA",    # cattail
    "ASSY",    # common milkweed
    "ECPU",    # purple coneflower
    "URDI",    # stinging nettle
    "PHAM4",   # pokeweed
    "HEMA17",  # giant hogweed
    "HEMA80",  # cowparsnip
]


def ensure_proto_db():
    conn = sqlite3.connect(PROTO_DB)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS distribution (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('state','county')),
            subdivision_name TEXT NOT NULL,
            nativity_code TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_distribution_species ON distribution(species_symbol);
        """
    )
    conn.commit()
    return conn


def pick_sample():
    all_symbols = []
    native_status = {}
    for f in CACHE_PROFILES.glob("*.json"):
        d = json.loads(f.read_text())
        profile = d.get("profile") or {}
        if profile.get("Id"):
            all_symbols.append((f.stem, profile["Id"]))
        statuses = profile.get("NativeStatuses") or []
        l48 = next((s for s in statuses if s.get("Region") == "L48"), None)
        if l48:
            native_status[f.stem] = l48.get("Status")

    by_symbol = dict(all_symbols)
    deliberate = [(s, by_symbol[s]) for s in DELIBERATE_SYMBOLS if s in by_symbol]
    missing = [s for s in DELIBERATE_SYMBOLS if s not in by_symbol]
    if missing:
        print(f"!! deliberate symbols not found in cache (skipped): {missing}", file=sys.stderr)

    remaining = [(s, pid) for s, pid in all_symbols if s not in DELIBERATE_SYMBOLS]
    random.seed(20261102)  # reproducible sample
    random_sample = random.sample(remaining, min(SAMPLE_SIZE - len(deliberate), len(remaining)))

    sample = deliberate + random_sample
    return sample, native_status


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
    sample, native_status = pick_sample()
    total = len(sample)
    print(f"Fetching real distribution data for {total} species ({len(DELIBERATE_SYMBOLS)} deliberate + "
          f"{total - len(DELIBERATE_SYMBOLS)} random)...")

    results = {}
    done = 0
    errors = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, sym, pid): sym for sym, pid in sample}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                r = fut.result()
                results[sym] = r
                if r["errors"]:
                    errors += 1
                    print(f"!! {sym}: {r['errors']}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"!! {sym}: hard failure: {e}", file=sys.stderr)
                results[sym] = {"states": [], "counties": [], "errors": [str(e)]}
                errors += 1
            done += 1
            if done % 25 == 0 or done == total:
                elapsed = time.time() - start
                print(f"{done}/{total}  ({elapsed:.0f}s elapsed)")
    elapsed_total = time.time() - start

    conn = ensure_proto_db()
    conn.execute("DELETE FROM distribution")  # idempotent re-run
    rows_inserted = 0
    level_singular = {"states": "state", "counties": "county"}
    for sym, r in results.items():
        for level in ("states", "counties"):
            for row in r[level]:
                conn.execute(
                    "INSERT INTO distribution (species_symbol, level, subdivision_name, nativity_code) VALUES (?,?,?,?)",
                    (sym, level_singular[level], row["name"], row["nativity_code"]),
                )
                rows_inserted += 1
    conn.commit()

    # --- Real stats, not estimated ---
    n_species = len(results)
    n_zero_state = sum(1 for r in results.values() if not r["states"])
    n_zero_county = sum(1 for r in results.values() if not r["counties"])
    state_counts = [len(r["states"]) for r in results.values()]
    county_counts = [len(r["counties"]) for r in results.values()]

    print("\n=== Real results ===")
    print(f"Species attempted: {n_species}, hard errors: {errors}")
    print(f"Species with zero state rows: {n_zero_state} ({100*n_zero_state/n_species:.1f}%)")
    print(f"Species with zero county rows: {n_zero_county} ({100*n_zero_county/n_species:.1f}%)")
    print(f"States per species: avg {sum(state_counts)/n_species:.1f}, max {max(state_counts)}")
    print(f"Counties per species: avg {sum(county_counts)/n_species:.1f}, max {max(county_counts)}")
    print(f"Total rows inserted (prototype db): {rows_inserted}")
    print(f"Elapsed: {elapsed_total:.0f}s for {n_species} species "
          f"({elapsed_total/n_species:.2f}s/species, {WORKERS} workers)")

    est_full = elapsed_total / n_species * 35326
    print(f"Real extrapolation to all 35,326 species at this measured rate: "
          f"~{est_full/3600:.1f} hours at {WORKERS} workers "
          f"(not a promise -- a government service's real behavior under sustained "
          f"load over hours is exactly what broke iNaturalist's and GBIF's own APIs "
          f"earlier in this project; a real full run needs retry/backoff headroom, "
          f"same lesson as Phase 1.10/1.11)")

    # --- Nativity-code crosswalk, cross-checked against already-known native_status ---
    print("\n=== Nativity-code crosswalk (plant_nativity_id vs. known L48 native_status) ===")
    code_votes = {}  # code -> {"N": n, "I": n}
    for sym, r in results.items():
        known = native_status.get(sym)
        if not known:
            continue
        for level in ("states", "counties"):
            for row in r[level]:
                code = row["nativity_code"]
                code_votes.setdefault(code, {"N": 0, "I": 0, "other": 0})
                if known in ("N", "I"):
                    code_votes[code][known] += 1
                else:
                    code_votes[code]["other"] += 1
    for code, votes in sorted(code_votes.items()):
        total_votes = sum(votes.values())
        print(f"  code {code!r}: N={votes['N']} I={votes['I']} other={votes['other']} "
              f"(n={total_votes}, {'likely NATIVE' if votes['N'] > votes['I'] else 'likely INTRODUCED' if votes['I'] > votes['N'] else 'unclear'})")

    print(f"\nPrototype database: {PROTO_DB}")
    print("Not wired into the live app, schema, or UI -- this is a real, measured "
          "validation pass only, same as every other bounded prototype in this project.")


if __name__ == "__main__":
    main()
