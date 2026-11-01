#!/usr/bin/env python3
"""Creates the real `field_notes` table on the master database (db.rs's
own `ensure_schema` only runs against a fresh dev database). v2's fourth
real deliverable: a user's own sighting, not an editorial claim --
deliberately has no `verified` column, unlike every other user-
contributed table. Idempotent: `CREATE TABLE IF NOT EXISTS`, safe to
re-run.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS field_notes (
    id INTEGER PRIMARY KEY,
    species_symbol TEXT REFERENCES species(symbol),
    observation TEXT NOT NULL,
    location TEXT,
    observed_at TEXT,
    added_by TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_field_notes_species ON field_notes(species_symbol);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("field_notes table ready")


if __name__ == "__main__":
    main()
