#!/usr/bin/env python3
"""Real replacement for ingest_inaturalist_images.py's live-API approach,
after that script hit sustained iNaturalist API rate-limiting partway
through a full-scale run (see ROADMAP.md Phase 1.9 -- 9,750 of 27,650
species attempted in ~18 hours before throttling made the remaining
~2.5 days impractical). Same goal, different mechanism: download the
real bulk Open Data exports once (observations.csv.gz, photos.csv.gz,
observers.csv.gz -- confirmed real columns via a byte-range peek before
committing to the full ~35GB download, not assumed from memory) and join
them locally instead of hitting the throttled REST API once per species.

Real sizes confirmed directly against the live bucket before downloading
anything: taxa.csv.gz 39MB, observers.csv.gz 20MB, observations.csv.gz
13.7GB, photos.csv.gz 21.1GB. Only the final per-image fetch touches the
network again, hitting S3's static photo URLs directly (the same ones
the live-API script already used successfully) -- not the api.inaturalist.org
REST endpoint that was doing the throttling.

Three real stages, each one real pass over its input, each resumable
(skips a stage whose output file already exists):
  1. Match our zero-image species against taxa.csv.gz (already have this
     downloaded from the earlier matching check -- 15,362 of 22,435
     zero-image species have an active iNaturalist taxon_id).
  2. Stream observations.csv.gz once: keep only
     (observation_uuid -> taxon_id) for a matched taxon with
     quality_grade='research'.
  3. Stream photos.csv.gz once: for each row whose observation_uuid
     survived stage 2 and whose license is CC0 or CC-BY, keep the first
     one found per taxon_id as that species' chosen photo.

Then, same as before: fetch the chosen photo's real bytes from
S3 and insert into images with source='inaturalist', verified=0 --
same unverified-by-default rule as every other non-USDA image.
"""
import csv
import gzip
import json
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"
BULK_DIR = Path(__file__).parent / "raw" / "inaturalist_bulk"
BASE_URL = "https://inaturalist-open-data.s3.amazonaws.com"
MAX_RETRIES = 4

FILES = {
    "taxa.csv.gz": f"{BASE_URL}/taxa.csv.gz",
    "observers.csv.gz": f"{BASE_URL}/observers.csv.gz",
    "observations.csv.gz": f"{BASE_URL}/observations.csv.gz",
    "photos.csv.gz": f"{BASE_URL}/photos.csv.gz",
}


def download_if_missing(name, url):
    """Shells out to curl with -C - (resume) rather than urllib -- these are
    multi-GB transfers over a multi-hour window, and a dropped connection
    partway through shouldn't mean starting a 21GB file over from scratch."""
    dest = BULK_DIR / name
    if dest.exists():
        print(f"  {name}: already downloaded ({dest.stat().st_size / 1e9:.2f} GB)", flush=True)
        return
    print(f"  {name}: downloading...", flush=True)
    start = time.time()
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(5):
        result = subprocess.run(
            ["curl", "-f", "-s", "-S", "-C", "-", "-o", str(tmp), url],
        )
        if result.returncode == 0:
            break
        print(f"  {name}: curl exited {result.returncode}, retrying ({attempt + 1}/5)...", flush=True)
        time.sleep(15)
    else:
        raise RuntimeError(f"failed to download {name} after 5 attempts")
    tmp.rename(dest)
    mins = (time.time() - start) / 60
    print(f"  {name}: done, {dest.stat().st_size / 1e9:.2f} GB in {mins:.1f} min", flush=True)


def stage_download():
    BULK_DIR.mkdir(parents=True, exist_ok=True)
    print("=== stage 1: download ===", flush=True)
    for name, url in FILES.items():
        download_if_missing(name, url)


def load_matched_taxa(conn):
    """symbol <- taxon_id, for species still missing an image only."""
    zero_image = set(
        r[0]
        for r in conn.execute(
            """SELECT symbol FROM species s WHERE NOT EXISTS (
                   SELECT 1 FROM images i
                   WHERE i.species_symbol=s.symbol AND i.is_public_domain=1
               )"""
        )
    )
    already_resolved = set(
        r[0] for r in conn.execute("SELECT species_symbol FROM images WHERE source='inaturalist'")
    )
    name_to_symbol = {}
    for symbol, sci_name in conn.execute("SELECT symbol, scientific_name FROM species"):
        if symbol not in zero_image or symbol in already_resolved:
            continue
        parts = sci_name.split()
        if len(parts) >= 2:
            name_to_symbol[(parts[0], parts[1].rstrip("."))] = symbol

    matched_taxa = {}  # taxon_id -> symbol
    with gzip.open(BULK_DIR / "taxa.csv.gz", "rt", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["rank"] != "species" or row["active"] != "true":
                continue
            parts = row["name"].split()
            if len(parts) < 2:
                continue
            symbol = name_to_symbol.get((parts[0], parts[1]))
            if symbol:
                matched_taxa[row["taxon_id"]] = symbol
    print(
        f"  {len(matched_taxa)} zero-image species have a matching active taxon_id "
        f"(of {len(zero_image) - len(already_resolved)} still needing one)",
        flush=True,
    )
    return matched_taxa


def stage_match_observations(matched_taxa):
    """One streaming pass over observations.csv.gz -- keep observation_uuid
    -> taxon_id only for a research-grade observation of a matched taxon."""
    print("=== stage 2: matching observations.csv.gz (one streaming pass) ===", flush=True)
    uuid_to_taxon = {}
    seen_taxa = set()
    start = time.time()
    with gzip.open(BULK_DIR / "observations.csv.gz", "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, row in enumerate(reader, 1):
            if i % 20_000_000 == 0:
                mins = (time.time() - start) / 60
                print(f"  ...{i:,} observation rows scanned, {mins:.1f} min, {len(uuid_to_taxon):,} matched so far", flush=True)
            taxon_id = row["taxon_id"]
            if taxon_id not in matched_taxa:
                continue
            if row["quality_grade"] != "research":
                continue
            # one observation is enough evidence for a given species; once we
            # have at least one candidate per taxon we don't need to keep
            # scanning for more of the *same* taxon's observations forever,
            # but we do keep every matching uuid since stage 3 still needs to
            # find one that actually has an eligible-licensed photo.
            uuid_to_taxon[row["observation_uuid"]] = taxon_id
            seen_taxa.add(taxon_id)
    mins = (time.time() - start) / 60
    print(
        f"  done: {len(uuid_to_taxon):,} research-grade observations kept, "
        f"covering {len(seen_taxa):,} of {len(matched_taxa):,} matched taxa, {mins:.1f} min",
        flush=True,
    )
    return uuid_to_taxon


def stage_match_photos(uuid_to_taxon):
    """One streaming pass over photos.csv.gz -- first eligible CC0/CC-BY
    photo per taxon_id wins; real file written so this stage, which is the
    slowest, doesn't have to be redone if a later stage fails."""
    out_path = BULK_DIR / "matched_photos.json"
    if out_path.exists():
        print(f"=== stage 3: already done, reusing {out_path.name} ===", flush=True)
        return json.loads(out_path.read_text())

    print("=== stage 3: matching photos.csv.gz (one streaming pass) ===", flush=True)
    chosen = {}  # taxon_id -> {photo_id, extension, license, observer_id}
    start = time.time()
    with gzip.open(BULK_DIR / "photos.csv.gz", "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, row in enumerate(reader, 1):
            if i % 20_000_000 == 0:
                mins = (time.time() - start) / 60
                print(f"  ...{i:,} photo rows scanned, {mins:.1f} min, {len(chosen):,} species resolved so far", flush=True)
            taxon_id = uuid_to_taxon.get(row["observation_uuid"])
            if not taxon_id or taxon_id in chosen:
                continue
            if row["license"].upper() not in ("CC0", "CC-BY"):
                continue
            chosen[taxon_id] = {
                "photo_id": row["photo_id"],
                "extension": row["extension"],
                "license": row["license"],
                "observer_id": row["observer_id"],
            }
    mins = (time.time() - start) / 60
    print(f"  done: {len(chosen):,} species resolved to a real licensed photo, {mins:.1f} min", flush=True)
    out_path.write_text(json.dumps(chosen))
    return chosen


def load_observer_names():
    names = {}
    with gzip.open(BULK_DIR / "observers.csv.gz", "rt", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            names[row["observer_id"]] = row.get("name") or row.get("login") or "iNaturalist contributor"
    return names


def fetch_with_backoff(url, timeout=15):
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    raise RuntimeError(f"exhausted retries for {url}")


def stage_fetch_and_insert(matched_taxa, chosen, observer_names, conn):
    print("=== stage 4: fetching real image bytes + inserting ===", flush=True)
    attribution_label = {"CC0": "no rights reserved (CC0)", "CC-BY": "some rights reserved (CC-BY)"}
    inserted = 0
    errors = 0
    for i, (taxon_id, symbol) in enumerate(matched_taxa.items(), 1):
        info = chosen.get(taxon_id)
        if not info:
            continue
        img_cache = BULK_DIR / f"img_{symbol}.{info['extension']}"
        try:
            if img_cache.exists():
                img_bytes = img_cache.read_bytes()
            else:
                url = f"{BASE_URL}/photos/{info['photo_id']}/medium.{info['extension']}"
                img_bytes = fetch_with_backoff(url)
                img_cache.write_bytes(img_bytes)

            observer = observer_names.get(info["observer_id"], "iNaturalist contributor")
            license_text = attribution_label.get(info["license"].upper(), f"({info['license']})")
            attribution = f"{observer}, {license_text}"

            conn.execute(
                """INSERT INTO images
                    (species_symbol, usda_image_id, url, is_public_domain, photographer,
                     institution, source, verified, added_at, data)
                   VALUES (?1, NULL, ?2, 1, ?3, 'iNaturalist (community, research-grade)',
                           'inaturalist', 0, datetime('now'), ?4)""",
                (
                    symbol,
                    f"{BASE_URL}/photos/{info['photo_id']}/medium.{info['extension']}",
                    attribution,
                    img_bytes,
                ),
            )
            conn.commit()
            inserted += 1
        except Exception as e:
            errors += 1
            print(f"  {symbol}: ERROR {e}", flush=True)

        if i % 1000 == 0:
            print(f"  [progress] {i}/{len(matched_taxa)} species checked, {inserted} inserted, {errors} errors", flush=True)

    print(flush=True)
    print(f"species checked: {len(matched_taxa)}")
    print(f"real photos inserted: {inserted}")
    print(f"errors: {errors}")


def main():
    stage_download()

    conn = sqlite3.connect(DB_PATH)
    matched_taxa = load_matched_taxa(conn)
    if not matched_taxa:
        print("nothing left to resolve", flush=True)
        return

    uuid_to_taxon = stage_match_observations(matched_taxa)
    chosen = stage_match_photos(uuid_to_taxon)
    observer_names = load_observer_names()
    stage_fetch_and_insert(matched_taxa, chosen, observer_names, conn)
    conn.close()


if __name__ == "__main__":
    main()
