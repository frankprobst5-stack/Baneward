#!/usr/bin/env python3
"""Adds two real, previously-unused USDA PLANTS datasets to the existing
35,326-species database:

1. Scientific-name synonyms (NameUsage.tsv's own synonym rows, 44,163
   total, 30,531 of which resolve directly to a species-rank accepted
   taxon already in our database -- the rest point to genus/family
   synthetic nodes or non-species ranks, deliberately not chased
   further). Lets a search for an older/alternate Latin name find the
   current accepted species.

2. PlantCharacteristics -- real structured morphology/growth/toxicity/
   use data, found via the real API endpoint
   (plantsservices.sc.egov.usda.gov/api/PlantCharacteristics/{id}, a
   path parameter, undocumented in the data package's own metadata).
   Only fetched for species whose cached PlantProfile already said
   HasCharacteristics=true (2,058 of 35,326, 5.8% -- real, confirmed
   coverage, not assumed universal) -- the other ~94% genuinely have
   nothing here, not worth a wasted API call each.

Resumable the same way ingest_full.py is: each species' characteristics
response is cached to data/cache_characteristics/<symbol>.json before
touching the database.
"""
import csv
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

HERE = Path(__file__).parent
RAW = HERE / "raw"
CACHE_PROFILES = HERE / "cache"
CACHE_CHAR = HERE / "cache_characteristics"
DB_PATH = HERE / "baneward.db"
API = "https://plantsservices.sc.egov.usda.gov/api"
HEADERS = {"User-Agent": "Baneward-ingest/0.1 (+github.com/frankprobst5-stack/Baneward; research/offline-reference use)"}
WORKERS = 10
RETRIES = 3


def ensure_tables(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            accepted_symbol TEXT NOT NULL REFERENCES species(symbol),
            scientific_name TEXT NOT NULL,
            authorship TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_synonyms_sciname ON synonyms(scientific_name);
        CREATE INDEX IF NOT EXISTS idx_synonyms_accepted ON synonyms(accepted_symbol);

        CREATE TABLE IF NOT EXISTS characteristics (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            name TEXT NOT NULL,
            value TEXT,
            category TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_characteristics_species ON characteristics(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_characteristics_name_value ON characteristics(name, value);
        """
    )
    conn.commit()


def ingest_synonyms(conn: sqlite3.Connection):
    accepted = {row[0] for row in conn.execute("SELECT symbol FROM species")}

    conn.execute("DELETE FROM synonyms")  # idempotent re-run
    rows = []
    with open(RAW / "NameUsage.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["col:status"] != "synonym":
                continue
            parent = row["col:parentID"]
            if parent not in accepted:
                continue
            rows.append((row["col:ID"], parent, row["col:scientificName"], row["col:authorship"]))

    conn.executemany(
        "INSERT INTO synonyms (symbol, accepted_symbol, scientific_name, authorship) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"Synonyms: {len(rows)} inserted (resolved to an accepted species already in the db)")


def species_with_characteristics():
    """Reads real plant ids straight from the already-fetched Phase 0
    cache -- no new PlantProfile calls needed, just the characteristics
    fetch itself."""
    out = []
    for f in CACHE_PROFILES.glob("*.json"):
        d = json.loads(f.read_text())
        profile = d.get("profile") or {}
        if profile.get("HasCharacteristics") and profile.get("Id"):
            out.append((f.stem, profile["Id"]))
    return out


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


def fetch_characteristics_one(symbol, plant_id):
    cache_file = CACHE_CHAR / f"{symbol}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    try:
        data = fetch_json(f"{API}/PlantCharacteristics/{plant_id}")
    except Exception as e:  # noqa: BLE001
        print(f"!! {symbol}: characteristics fetch failed: {e}", file=sys.stderr)
        return []
    cache_file.write_text(json.dumps(data))
    return data


def ingest_characteristics(conn: sqlite3.Connection):
    CACHE_CHAR.mkdir(exist_ok=True)
    targets = species_with_characteristics()
    total = len(targets)
    print(f"{total} species with real HasCharacteristics=true to fetch")

    results = {}
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_characteristics_one, sym, pid): sym for sym, pid in targets}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                results[sym] = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"!! {sym}: {e}", file=sys.stderr)
                results[sym] = []
            done += 1
            if done % 250 == 0 or done == total:
                elapsed = time.time() - start
                print(f"{done}/{total}  ({elapsed:.0f}s elapsed)")

    conn.execute("DELETE FROM characteristics")  # idempotent re-run
    rows_inserted = 0
    for sym, rows in results.items():
        for row in rows:
            conn.execute(
                "INSERT INTO characteristics (species_symbol, name, value, category) VALUES (?,?,?,?)",
                (
                    sym,
                    row.get("PlantCharacteristicName"),
                    row.get("PlantCharacteristicValue"),
                    row.get("PlantCharacteristicCategory"),
                ),
            )
            rows_inserted += 1
    conn.commit()
    print(f"Characteristics: {rows_inserted} rows across {len(results)} species")


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)
    ingest_synonyms(conn)
    ingest_characteristics(conn)
    conn.close()


if __name__ == "__main__":
    main()
