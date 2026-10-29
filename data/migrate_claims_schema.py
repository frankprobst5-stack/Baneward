#!/usr/bin/env python3
"""One-time schema migration: `tags` -> `claims`, adding the real
evidence-type/plant-part/reference/region fields a reviewed design pass
called for (see ROADMAP.md Phase 1.5/1.6). Idempotent: safe to run again
on a database that's already migrated (detects an existing `claims`
table and does nothing).

Old column -> new column mapping (1:1, nothing lost):
  tag_type  -> category
  value     -> description
  (new)     -> plant_part        (NULL for existing rows)
  (new)     -> evidence_type     ('unspecified' for existing rows)
  verified  -> verified
  source    -> source
  (new)     -> reference         (NULL for existing rows)
  (new)     -> region            (NULL for existing rows)
  added_by  -> added_by
  added_at  -> added_at
  (new)     -> verified_by       (NULL for existing rows)
  (new)     -> verified_at       (NULL for existing rows)
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"

SCHEMA = """
CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    species_symbol TEXT NOT NULL REFERENCES species(symbol),
    category TEXT NOT NULL CHECK(category IN ('medical','poisonous','edible','useful')),
    plant_part TEXT,
    description TEXT NOT NULL,
    evidence_type TEXT NOT NULL DEFAULT 'unspecified'
        CHECK(evidence_type IN ('traditional','laboratory','animal_study','human_clinical','regulatory','unspecified')),
    verified INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    reference TEXT,
    region TEXT,
    added_by TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    verified_by TEXT,
    verified_at TEXT
);
CREATE INDEX idx_claims_species ON claims(species_symbol);
CREATE INDEX idx_claims_category ON claims(category);
"""


def migrate(conn: sqlite3.Connection):
    existing_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "claims" in existing_tables:
        print("Already migrated -- claims table exists, nothing to do.")
        return

    conn.executescript(SCHEMA)

    if "tags" in existing_tables:
        rows = conn.execute(
            "SELECT species_symbol, tag_type, value, verified, source, added_by, added_at FROM tags"
        ).fetchall()
        conn.executemany(
            """INSERT INTO claims
               (species_symbol, category, description, verified, source, added_by, added_at)
               VALUES (?,?,?,?,?,?,?)""",
            rows,
        )
        conn.execute("DROP TABLE tags")
        print(f"Migrated {len(rows)} row(s) from tags -> claims, dropped tags.")
    else:
        print("No existing tags table found -- created an empty claims table.")

    conn.commit()


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    migrate(conn)
    conn.close()
