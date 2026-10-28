#!/usr/bin/env python3
"""Adds the one real demonstration tag proving the add/verify mechanism
works. Deliberately separate from ingest_full.py: that script's own
build_db() drops and recreates the whole database on every run (by
design, for reproducibility against a fresh USDA fetch) -- baking a
"real" tag into that rebuild path would make it look like ingested data
instead of what it actually is, a deliberate one-off demonstration.
Idempotent: safe to run again, won't duplicate the row.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"


def main():
    con = sqlite3.connect(DB_PATH)
    existing = con.execute(
        "SELECT id FROM tags WHERE species_symbol='CIMA2' AND tag_type='poisonous'"
    ).fetchone()
    if existing:
        print(f"Demo tag already present (id {existing[0]}), nothing to do.")
        return

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
    print("Demo tag added.")


if __name__ == "__main__":
    main()
