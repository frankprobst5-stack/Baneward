#!/usr/bin/env python3
"""Adds provenance/review columns to the real `images` table so a
user-uploaded photo can be tracked the same way a `claims` row already
is -- source, verified (default 0 for a new upload), added_by, added_at,
verified_by, verified_at.

Existing rows (all from the original USDA PLANTS ingest) are backfilled
as source='usda_plants', verified=1 -- that's institutional data already
tied to the right species by USDA's own curation, not a new identification
claim someone just made, so it isn't held to the same unverified-by-default
rule a brand new upload is.

Also adds `data BLOB` (2026-10-29, for data/ingest_inaturalist_images.py):
externally-sourced images we actually have the right bytes for (CC0/CC-BY)
get cached directly in the row instead of just storing another live URL --
USDA's own images stay URL-only (unchanged, a much bigger re-ingest to
redo), but a community-sourced photo is pointless for a grid-down app if
it still needs the internet to actually render. Idempotent: safe to re-run.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(images)")}

    additions = [
        ("source", "TEXT NOT NULL DEFAULT 'usda_plants'"),
        ("verified", "INTEGER NOT NULL DEFAULT 1"),
        ("added_by", "TEXT"),
        ("added_at", "TEXT"),
        ("verified_by", "TEXT"),
        ("verified_at", "TEXT"),
        ("data", "BLOB"),
    ]
    for col, decl in additions:
        if col in existing:
            print(f"column '{col}' already present, skipping")
            continue
        conn.execute(f"ALTER TABLE images ADD COLUMN {col} {decl}")
        print(f"added column '{col}'")

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    usda = conn.execute("SELECT COUNT(*) FROM images WHERE source='usda_plants'").fetchone()[0]
    print(f"real counts after migration: {total} total images, {usda} source='usda_plants'")
    conn.close()


if __name__ == "__main__":
    main()
