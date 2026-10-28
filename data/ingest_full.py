#!/usr/bin/env python3
"""Full-scale USDA PLANTS ingest -- all ~35,000 accepted, species-rank
taxa (not varieties/subspecies/synonyms; a forager doesn't need
"Cicuta maculata var. angustifolia" distinguished from the species
itself). Same real pipeline build_phase0.py proved on 10 species,
scaled up: real rate-limited, resumable, cached calls against USDA's
live enrichment API -- not a toy loop against a production government
service.

Resumable by design: each species' PlantProfile/PlantImages responses
are cached to data/cache/<symbol>.json before anything touches the
database, so a killed/restarted run never re-fetches what it already
has. Safe to Ctrl-C and rerun.

Concurrency: 10 threads, matching the known-safe figure the GBIF
package's own metadata.yaml documents for this exact API (same
generator author's real-world experience, not guessed).
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
CACHE = HERE / "cache"
DB_PATH = HERE / "baneward.db"
API = "https://plantsservices.sc.egov.usda.gov/api"
IMG_BASE = "https://plants.sc.egov.usda.gov"
HEADERS = {"User-Agent": "Baneward-ingest/0.1 (+github.com/frankprobst5-stack/Baneward; research/offline-reference use)"}
WORKERS = 10
RETRIES = 3


def load_accepted_species():
    """Real taxonomy straight from the CC0 TSV -- accepted, species rank
    only. Returns {symbol: {scientific_name, authorship, family, link}}."""
    out = {}
    with open(RAW / "NameUsage.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["col:status"] == "accepted" and row["col:rank"] == "species" and row["col:link"]:
                out[row["col:ID"]] = {
                    "scientific_name": row["col:scientificName"],
                    "authorship": row["col:authorship"],
                    "family": row["col:family"],
                    "link": row["col:link"],
                }
    return out


def load_common_names():
    """First English common name per symbol, same as build_phase0.py."""
    out = {}
    with open(RAW / "VernacularName.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sym = row["col:taxonID"]
            if sym not in out:
                out[sym] = row["col:name"]
    return out


def fetch_json(url, params, retries=RETRIES):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 -- real transient network/5xx errors, retry regardless of shape
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {url} {params}: {last_err}")


def enrich_one(symbol):
    """Fetch (or load from cache) PlantProfile + PlantImages for one
    symbol. Returns the combined dict, or None if the real API has
    nothing for this symbol (logged, not fatal -- a handful of symbols
    not resolving isn't a reason to kill a 35,000-species run)."""
    cache_file = CACHE / f"{symbol}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    try:
        profile = fetch_json(f"{API}/PlantProfile", {"symbol": symbol})
    except Exception as e:  # noqa: BLE001
        print(f"!! {symbol}: profile fetch failed: {e}", file=sys.stderr)
        return None

    images = []
    plant_id = profile.get("Id")
    if plant_id:
        try:
            images = fetch_json(f"{API}/PlantImages", {"plantId": plant_id}) or []
        except Exception as e:  # noqa: BLE001
            print(f"!! {symbol}: images fetch failed: {e}", file=sys.stderr)

    result = {"profile": profile, "images": images}
    cache_file.write_text(json.dumps(result))
    return result


def main():
    CACHE.mkdir(exist_ok=True)
    species = load_accepted_species()
    common = load_common_names()
    symbols = list(species.keys())
    total = len(symbols)
    print(f"{total} accepted species-rank taxa to ingest (cached ones skip the real API call)")

    results = {}
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(enrich_one, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                results[sym] = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"!! {sym}: {e}", file=sys.stderr)
                results[sym] = None
            done += 1
            if done % 250 == 0 or done == total:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed else 0
                remaining = (total - done) / rate if rate else 0
                print(f"{done}/{total}  ({elapsed/60:.1f}m elapsed, ~{remaining/60:.1f}m left)")

    build_db(species, common, results)


def build_db(species, common, results):
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE species (
            symbol TEXT PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            authorship TEXT,
            common_name TEXT,
            family TEXT,
            duration TEXT,
            growth_habit TEXT,
            native_status TEXT,
            source TEXT DEFAULT 'USDA PLANTS',
            source_url TEXT,
            enriched_at TEXT
        );
        CREATE TABLE images (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            usda_image_id INTEGER,
            url TEXT NOT NULL,
            is_public_domain INTEGER NOT NULL,
            photographer TEXT,
            institution TEXT
        );
        -- Starts EMPTY for every species. A missing row means "not yet
        -- classified" -- never inferred as safe.
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            tag_type TEXT NOT NULL CHECK(tag_type IN ('medical','poisonous','edible','useful')),
            value TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            added_by TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_species_sciname ON species(scientific_name);
        CREATE INDEX idx_species_common ON species(common_name);
        CREATE INDEX idx_images_species ON images(species_symbol);
        CREATE INDEX idx_tags_species ON tags(species_symbol);
    """)

    inserted = skipped = 0
    for sym, info in species.items():
        r = results.get(sym)
        profile = (r or {}).get("profile") or {}
        con.execute(
            """INSERT INTO species
               (symbol, scientific_name, authorship, common_name, family,
                duration, growth_habit, native_status, source_url, enriched_at)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (
                sym,
                info["scientific_name"],
                info["authorship"],
                common.get(sym, profile.get("CommonName")),
                info["family"],
                ", ".join(profile.get("Durations") or []),
                ", ".join(profile.get("GrowthHabits") or []),
                ", ".join(f"{n['Region']} {n['Status']}" for n in (profile.get("NativeStatuses") or [])),
                info["link"],
            ),
        )
        if r:
            inserted += 1
            for img in r.get("images") or []:
                con.execute(
                    """INSERT INTO images
                       (species_symbol, usda_image_id, url, is_public_domain, photographer, institution)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        sym,
                        img.get("ImageID"),
                        IMG_BASE + img["StandardSizeImageLibraryPath"],
                        0 if img.get("Copyright") else 1,
                        img.get("CommonName"),
                        img.get("InstitutionName"),
                    ),
                )
        else:
            skipped += 1

    con.commit()
    con.close()
    print(f"\nBuilt {DB_PATH}: {inserted} enriched, {skipped} name-only (API fetch failed for those)")


if __name__ == "__main__":
    main()
