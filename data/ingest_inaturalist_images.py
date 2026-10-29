#!/usr/bin/env python3
"""Fills in real photos for species that have none, from iNaturalist's live
API -- CC0/CC-BY, research-grade (community identification consensus)
observations only. Real-world validated before this was written: a bounded
50-species test against the live API found a usable photo for 40/50 (80%)
of our zero-image species (see ROADMAP.md Phase 1.8).

Caches the actual image bytes directly into the `images.data` BLOB column
(data/migrate_images_schema.py) rather than just storing another live URL
-- a community-sourced photo is pointless for a grid-down app if it still
needs the internet to render. Deliberately conservative about trust: a
research-grade iNaturalist ID is a real quality signal (2+ independent
identifiers agreed), stronger than a single unreviewed upload, but it's
still a community identification, not USDA's own institutional tie --
inserted as source='inaturalist', verified=0, same unverified-by-default
rule as everything else that isn't USDA's own data.

Resumable: raw API responses and downloaded image bytes are cached to
disk under data/raw/inaturalist/, so a re-run (or a later, larger run)
doesn't re-fetch species already resolved. Rate-limited to iNaturalist's
own documented ~1 req/sec guidance.

Deliberately bounded by default (--limit) -- this is a prototype run to
prove the real approach end-to-end before deciding whether/how to scale
to all ~27,650 zero-image species. At iNaturalist's own rate-limit
guidance, resolving all of them through this live per-species API would
take on the order of 7-8 hours sequential; a real full-scale pass should
likely use the bulk Open Data metadata dump instead (see ROADMAP.md) --
not attempted here.
"""
import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"
CACHE_DIR = Path(__file__).parent / "raw" / "inaturalist"
API = "https://api.inaturalist.org/v1/observations"
RATE_LIMIT_SECONDS = 1.1


def load_zero_image_species(conn):
    rows = conn.execute(
        """SELECT symbol, scientific_name FROM species s
           WHERE NOT EXISTS (
               SELECT 1 FROM images i
               WHERE i.species_symbol = s.symbol AND i.is_public_domain = 1
           )
           ORDER BY symbol"""
    ).fetchall()
    return rows


def already_resolved(conn, symbol):
    return conn.execute(
        "SELECT 1 FROM images WHERE species_symbol = ?1 AND source = 'inaturalist'",
        (symbol,),
    ).fetchone() is not None


def fetch_observation(two_word_name, cache_path):
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    query = urllib.parse.urlencode(
        {
            "taxon_name": two_word_name,
            "photos": "true",
            "photo_license": "cc0,cc-by",
            "quality_grade": "research",
            "per_page": 3,
        }
    )
    with urllib.request.urlopen(f"{API}?{query}", timeout=10) as r:
        data = json.load(r)
    cache_path.write_text(json.dumps(data))
    return data


def pick_photo(data, two_word_name):
    for result in data.get("results", []):
        taxon = result.get("taxon") or {}
        if taxon.get("name") != two_word_name:
            continue  # real guard: don't accept a loosely-matched different taxon
        for photo in result.get("photos", []):
            if photo.get("license_code") in ("cc0", "cc-by") and not photo.get("hidden"):
                return photo
    return None


def download_bytes(photo, img_cache_path):
    if img_cache_path.exists():
        return img_cache_path.read_bytes()
    url = photo["url"].replace("square.jpg", "medium.jpg")
    with urllib.request.urlopen(url, timeout=15) as r:
        content = r.read()
    img_cache_path.write_bytes(content)
    return content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="how many zero-image species to attempt this run")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    species = load_zero_image_species(conn)
    print(f"{len(species)} species currently have zero usable images")

    attempted = 0
    found = 0
    no_match = 0
    errors = 0

    for symbol, sci_name in species:
        if already_resolved(conn, symbol):
            continue
        if attempted >= args.limit:
            break
        attempted += 1

        parts = sci_name.split()
        two_word_name = " ".join(parts[:2]) if len(parts) >= 2 else sci_name

        try:
            obs_cache = CACHE_DIR / f"{symbol}.json"
            data = fetch_observation(two_word_name, obs_cache)
            if not obs_cache.exists() or obs_cache.stat().st_size == 0:
                time.sleep(RATE_LIMIT_SECONDS)

            photo = pick_photo(data, two_word_name)
            if not photo:
                no_match += 1
                continue

            img_cache = CACHE_DIR / f"{symbol}.jpg"
            img_bytes = download_bytes(photo, img_cache)

            conn.execute(
                """INSERT INTO images
                    (species_symbol, usda_image_id, url, is_public_domain, photographer,
                     institution, source, verified, added_at, data)
                   VALUES (?1, NULL, ?2, 1, ?3, 'iNaturalist (community, research-grade)',
                           'inaturalist', 0, datetime('now'), ?4)""",
                (
                    symbol,
                    photo["url"].replace("square.jpg", "medium.jpg"),
                    photo.get("attribution"),
                    img_bytes,
                ),
            )
            conn.commit()
            found += 1
        except Exception as e:
            errors += 1
            print(f"  {symbol} ({two_word_name}): ERROR {e}")

    print()
    print(f"attempted: {attempted}")
    print(f"found + cached: {found}")
    print(f"no CC0/CC-BY research-grade match: {no_match}")
    print(f"errors: {errors}")
    conn.close()


if __name__ == "__main__":
    main()
