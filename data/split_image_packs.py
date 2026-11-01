#!/usr/bin/env python3
"""Splits the cached community-photo bytes (iNaturalist/Wikidata/Smithsonian,
Phases 1.9-1.11) out of the main bundled database into separate per-source
"pack" files -- GitHub rejected pushing the combined database once it passed
2GB, a hard per-file LFS limit, not the account's overall storage quota.
Each source's pack happens to land comfortably under that limit on its own
(iNaturalist ~1.95GB, Smithsonian ~0.78GB, Wikidata ~0.08GB), so splitting
by source is a natural, not arbitrary, boundary.

The main `baneward.db` keeps every image's row (url, photographer, source,
verified, etc.) -- only the heavy `data` BLOB moves out, replaced with NULL
until a pack is downloaded and applied (app/src-tauri/src/commands.rs's
`download_image_pack`, same ATTACH DATABASE + UPDATE pattern used all
session for merging data into the live app). This is what makes the
*installer* lean again (back near Phase 1.8's ~67MB) while still letting a
user who wants the full offline photo set get it after install -- the
real fix, not a smaller version of the same 2GB-ceiling problem down the
road as coverage keeps growing.

Idempotent-ish: refuses to re-split a source whose pack file already
exists, so a partial re-run doesn't double up.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"
PACKS_DIR = Path(__file__).parent / "image_packs"
SOURCES = ["inaturalist", "wikidata_commons", "smithsonian"]


def main():
    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    before = DB_PATH.stat().st_size
    print(f"main db before: {before/1e9:.2f} GB")

    for source in SOURCES:
        pack_path = PACKS_DIR / f"{source}.db"
        if pack_path.exists():
            print(f"{source}: pack already exists, skipping")
            continue

        rows = conn.execute(
            "SELECT id, data FROM images WHERE source=?1 AND data IS NOT NULL", (source,)
        ).fetchall()
        if not rows:
            print(f"{source}: no rows with data to split, skipping")
            continue

        pack_conn = sqlite3.connect(pack_path)
        pack_conn.execute("CREATE TABLE pack (id INTEGER PRIMARY KEY, data BLOB NOT NULL)")
        pack_conn.executemany("INSERT INTO pack (id, data) VALUES (?, ?)", rows)
        pack_conn.commit()
        pack_conn.close()

        real_pack_size = pack_path.stat().st_size
        print(f"{source}: {len(rows)} images -> {pack_path.name} ({real_pack_size/1e9:.2f} GB)")

        conn.execute("UPDATE images SET data = NULL WHERE source=?1", (source,))
        conn.commit()

    print("vacuuming main db to reclaim space...")
    conn.execute("VACUUM")
    conn.close()

    after = DB_PATH.stat().st_size
    print(f"main db after: {after/1e9:.2f} GB (was {before/1e9:.2f} GB)")


if __name__ == "__main__":
    main()
