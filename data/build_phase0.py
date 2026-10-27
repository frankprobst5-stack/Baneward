#!/usr/bin/env python3
"""Phase 0 pipeline prototype: USDA PLANTS (CC0 taxonomy + real enrichment
API) populates the species/images tables; the tags table starts EMPTY per
species -- medical/poisonous/edible/useful get added later, by a human or a
future sourcing pass, never defaulted to a claim. One demonstration tag is
added at the end for water hemlock, sourced and marked verified, purely to
prove the tagging mechanism itself works -- not a real editorial pass.

Real USDA PLANTS data, real API calls, real sample of symbols chosen to
cover the project's actual mission: well-known deadly plants, well-known
edibles, and a classic dangerous look-alike pair (poison hemlock vs. wild
carrot).
"""
import csv
import sqlite3
import sys
import time
from pathlib import Path

import requests

RAW = Path(__file__).parent / "raw"
DB_PATH = Path(__file__).parent / "baneward.db"
API = "https://plantsservices.sc.egov.usda.gov/api"
IMG_BASE = "https://plants.sc.egov.usda.gov"
HEADERS = {"User-Agent": "Baneward-Phase0-prototype/0.1 (+github.com/frankprobst5-stack/Baneward)"}

# Real, deliberately chosen sample: deadly plants, common edibles/medicinals,
# and the classic poison-hemlock/wild-carrot look-alike pair that's exactly
# the kind of real danger this project exists to help with.
SAMPLE_SYMBOLS = [
    "CIMA2",  # Cicuta maculata -- water hemlock, one of NA's deadliest plants
    "COMA2",  # Conium maculatum -- poison hemlock
    "DACA6",  # Daucus carota -- wild carrot/Queen Anne's lace, looks like hemlock, edible root
    "TODI",   # Toxicodendron diversilobum -- poison oak
    "TORA2",  # Toxicodendron radicans -- poison ivy
    "URDI",   # Urtica dioica -- stinging nettle, edible cooked, stings raw
    "ASSY",   # Asclepias syriaca -- common milkweed, edible if prepared right
    "ECPU",   # Echinacea purpurea -- medicinal
    "TYLA",   # Typha latifolia -- cattail, classic wild edible
    "PHAM4",  # Phytolacca americana -- pokeweed, toxic raw, edible only if prepared correctly
]


def load_names_and_families(symbols):
    """Pull scientific name + family straight from the real CC0 TSV dump,
    not the API -- this is the bulk source, the API is just enrichment."""
    found = {}
    with open(RAW / "NameUsage.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sym = row["col:ID"]
            if sym in symbols:
                found[sym] = {
                    "scientific_name": row["col:scientificName"],
                    "authorship": row["col:authorship"],
                    "family": row["col:family"],
                    "status": row["col:status"],
                    "link": row["col:link"],
                }
    return found


def load_common_names(symbols):
    names = {}
    with open(RAW / "VernacularName.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sym = row["col:taxonID"]
            if sym in symbols and sym not in names:
                names[sym] = row["col:name"]
    return names


def enrich(symbol):
    """Real API call -- distribution, growth habit, duration, plant id
    (needed for the images call)."""
    r = requests.get(f"{API}/PlantProfile", params={"symbol": symbol}, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_images(plant_id):
    """Real API call -- per-image copyright flag is the whole reason this
    is a separate call from PlantProfile."""
    r = requests.get(f"{API}/PlantImages", params={"plantId": plant_id}, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json() or []


def build():
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

        -- Starts EMPTY per species. A missing row means "not yet
        -- classified" -- never inferred as safe. Matches the project's
        -- own safety rule in README.md.
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
    """)

    names = load_names_and_families(SAMPLE_SYMBOLS)
    common = load_common_names(SAMPLE_SYMBOLS)

    for sym in SAMPLE_SYMBOLS:
        if sym not in names:
            print(f"!! {sym} not found in NameUsage.tsv -- skipping", file=sys.stderr)
            continue
        info = names[sym]
        print(f"Enriching {sym} ({info['scientific_name']})...")
        profile = enrich(sym)
        time.sleep(0.3)  # real USDA service, not hammering it for a 10-row prototype

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

        plant_id = profile.get("Id")
        if plant_id:
            for img in fetch_images(plant_id):
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
            time.sleep(0.3)

    # One real, well-sourced demonstration tag -- proves the editable-tag
    # mechanism end to end. Not a production editorial pass: a single,
    # about-as-uncontested-as-it-gets fact (water hemlock is deadly,
    # agreed by every real poison-plant reference, CDC included), entered
    # the same way a real future entry would be: verified=1 with a cited
    # source, not just asserted.
    con.execute(
        """INSERT INTO tags (species_symbol, tag_type, value, verified, source, added_by)
           VALUES (?,?,?,?,?,?)""",
        (
            "CIMA2",
            "poisonous",
            "Contains cicutoxin; among the most acutely toxic plants in North America -- "
            "ingestion can cause fatal seizures within hours. Root/rhizome are the most "
            "dangerous parts.",
            1,
            "CDC NIOSH; USDA ARS Poisonous Plant Research Laboratory (Logan, UT) publications",
            "phase0-prototype",
        ),
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    build()
    print(f"\nBuilt {DB_PATH}")
