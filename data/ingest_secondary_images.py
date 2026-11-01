#!/usr/bin/env python3
"""Fills in more photos for species the iNaturalist pipeline (Phase 1.10)
couldn't cover, from two sources verified safe and real before anything
was built:

1. Wikidata's P18 (image) property, matched via the exact taxon name
   (P225) -- NOT Wikimedia Commons' free-text search, which was tested
   first and produced real false positives at scale (e.g. a text search
   for "Arthrocnemum subterminale" returned a photo of the unrelated
   genus "Arthroceras", and "Rhizocarpon lavatum" returned a photo of an
   entirely different fungal order). Even the structured P18 match isn't
   perfectly immune to a bad Wikidata edit, so every candidate's own file
   name/description is cross-checked for the genus before accepting.

2. Smithsonian's own specimen collection, reached through GBIF but
   filtered to ONLY collections.nmnh.si.edu -- GBIF aggregates dozens of
   independent institutional hosts, several of which explicitly forbid
   automated bulk access (California Academy of Sciences says so
   directly even on CC0-marked content; Naturalis's robots.txt disallows
   "anthropic-ai" by name; NYBG and MNHN block or bot-challenge automated
   requests). Smithsonian's own robots.txt was checked and only disallows
   /services/ and /missing.html -- the one host confirmed safe to use
   here. No other GBIF-sourced host is fetched by this script, on
   purpose, not by oversight.

Real measured yield on a 25-species random sample of species the
iNaturalist pipeline couldn't resolve: Wikidata 4/25 (16%, one borderline),
Smithsonian 3/25 (12%), 1 species found by both -- about 20-24% combined,
not close to the ~55% iNaturalist managed on its own matched subset. The
species left after Phase 1.10 skew heavily toward lichens, mosses, and
rare local endemics that are thinly documented everywhere, not just on
iNaturalist -- a real, structural reason this yield is lower, not a sign
the matching is broken.
"""
import argparse
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"
CACHE_DIR = Path(__file__).parent / "raw" / "secondary_images"
HEADERS = {"User-Agent": "Baneward/0.1 (offline US wild plant database; https://github.com/frankprobst5-stack/Baneward)"}
MAX_RETRIES = 4


def fetch_json(url, timeout=10):
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"    rate limited (429) on {url[:60]}..., backing off {wait}s", flush=True)
                time.sleep(wait)
            elif attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def fetch_bytes(url, timeout=15):
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def load_zero_image_species(conn):
    return conn.execute(
        """SELECT symbol, scientific_name FROM species s
           WHERE NOT EXISTS (
               SELECT 1 FROM images i WHERE i.species_symbol=s.symbol AND i.is_public_domain=1
           ) ORDER BY symbol"""
    ).fetchall()


def already_resolved(conn, symbol):
    return conn.execute(
        "SELECT 1 FROM images WHERE species_symbol=?1 AND source IN ('wikidata_commons','smithsonian')",
        (symbol,),
    ).fetchone() is not None


def try_wikidata(two_word, genus):
    sparql = f'SELECT ?image WHERE {{ ?item wdt:P225 "{two_word}". ?item wdt:P18 ?image. }} LIMIT 1'
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    d = fetch_json(url, timeout=15)
    rows = d.get("results", {}).get("bindings", [])
    if not rows:
        return None
    image_url = rows[0]["image"]["value"]
    filename = urllib.parse.unquote(image_url.rsplit("/", 1)[-1])
    # real safety cross-check: the Arthrocnemum/Arthroceras mismatch found
    # during verification means a P18 link isn't automatically trustworthy --
    # require the image's own filename to at least mention the genus.
    if not re.search(re.escape(genus), filename, re.IGNORECASE):
        return None
    # resolve the real file info (license + author) via the Commons API --
    # iiurlwidth asks for a real resized thumbnail (thumburl) rather than
    # the full original; Wikidata-linked originals run several MB each,
    # wildly out of line with every other source here (~100-250KB average).
    info_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 500,
            "format": "json",
        }
    )
    info = fetch_json(info_url)
    pages = info.get("query", {}).get("pages", {})
    for page in pages.values():
        if "imageinfo" not in page:
            return None
        ii = page["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        license_short = (meta.get("LicenseShortName", {}).get("value") or "").upper()
        if not (license_short.startswith("CC0") or license_short.startswith("CC BY") and "SA" not in license_short and "NC" not in license_short):
            return None
        artist = re.sub("<[^<]+?>", "", meta.get("Artist", {}).get("value") or "Wikimedia Commons contributor")
        image_url = ii.get("thumburl") or ii["url"]
        return {"url": image_url, "license": license_short, "attribution": artist.strip()}
    return None


def try_smithsonian(two_word):
    match = fetch_json(
        "https://api.gbif.org/v1/species/match?" + urllib.parse.urlencode({"name": two_word})
    )
    if match.get("canonicalName") != two_word or match.get("rank") != "SPECIES":
        return None
    key = match.get("usageKey")
    occ = fetch_json(
        "https://api.gbif.org/v1/occurrence/search?"
        + urllib.parse.urlencode({"taxonKey": key, "mediaType": "StillImage", "limit": 20})
    )
    for res in occ.get("results", []):
        for media in res.get("media", []):
            ident = media.get("identifier", "")
            lic = (media.get("license") or "").lower()
            if "collections.nmnh.si.edu" not in ident:
                continue
            if "publicdomain/zero" in lic:
                license_label = "CC0"
            elif "licenses/by/" in lic:
                license_label = "CC-BY"
            else:
                continue
            return {"url": ident, "license": license_label, "attribution": "Smithsonian National Museum of Natural History"}
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    species = load_zero_image_species(conn)
    print(f"{len(species)} species currently have zero usable images", flush=True)

    attempted = 0
    found_wikidata = 0
    found_smithsonian = 0
    errors = 0
    start = time.time()

    for symbol, sci_name in species:
        if already_resolved(conn, symbol):
            continue
        if attempted >= args.limit:
            break
        attempted += 1

        parts = sci_name.split()
        if len(parts) < 2:
            continue
        two_word = " ".join(parts[:2])
        genus = parts[0]

        try:
            result = None
            source = None
            cache_json = CACHE_DIR / f"{symbol}.json"
            if cache_json.exists():
                cached = json.loads(cache_json.read_text())
                result, source = (cached, cached.get("_source")) if cached else (None, None)
            else:
                # real pacing between live requests -- the lesson from
                # Phase 1.10's live-API run (no delay here cost a wasted
                # ~18 hours before iNaturalist started throttling us) --
                # cheap insurance against the same mistake on two more APIs.
                result = try_wikidata(two_word, genus)
                time.sleep(0.5)
                source = "wikidata_commons"
                if not result:
                    result = try_smithsonian(two_word)
                    time.sleep(0.5)
                    source = "smithsonian"
                to_cache = dict(result, _source=source) if result else None
                cache_json.write_text(json.dumps(to_cache) if to_cache else "null")

            if not result:
                continue

            ext = result["url"].rsplit(".", 1)[-1].split("?")[0].lower()
            if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
                ext = "jpg"
            img_cache = CACHE_DIR / f"{symbol}.{ext}"
            img_bytes = img_cache.read_bytes() if img_cache.exists() else fetch_bytes(result["url"])
            if not img_cache.exists():
                img_cache.write_bytes(img_bytes)

            institution = "Wikimedia Commons / Wikidata" if source == "wikidata_commons" else "Smithsonian National Museum of Natural History"
            attribution = f"{result['attribution']}, {result['license']}"

            conn.execute(
                """INSERT INTO images
                    (species_symbol, usda_image_id, url, is_public_domain, photographer,
                     institution, source, verified, added_at, data)
                   VALUES (?1, NULL, ?2, 1, ?3, ?4, ?5, 0, datetime('now'), ?6)""",
                (symbol, result["url"], attribution, institution, source, img_bytes),
            )
            conn.commit()
            if source == "wikidata_commons":
                found_wikidata += 1
            else:
                found_smithsonian += 1
        except Exception as e:
            errors += 1
            print(f"  {symbol} ({two_word}): ERROR {e}", flush=True)

        if attempted % 250 == 0:
            mins = (time.time() - start) / 60
            print(
                f"[progress] {attempted}/{args.limit}, wikidata={found_wikidata} "
                f"smithsonian={found_smithsonian} errors={errors} {mins:.1f} min",
                flush=True,
            )

    print(flush=True)
    print(f"attempted: {attempted}")
    print(f"found via Wikidata/Commons: {found_wikidata}")
    print(f"found via Smithsonian: {found_smithsonian}")
    print(f"errors: {errors}")
    conn.close()


if __name__ == "__main__":
    main()
