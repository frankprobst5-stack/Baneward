#!/usr/bin/env python3
"""Real bug found while building the v2 identification wizard (2026-11-01),
not introduced by it: Phase 1.5's own characteristics ingest
(data/ingest_characteristics_and_synonyms.py) left exact duplicate rows in
the `characteristics` table for many species -- one species (tall fescue,
SCAR7) had every one of its ~80 real traits duplicated 25 times over
(2,001 rows for one species). Real scope, checked directly before writing
this: 200,872 total rows, only 163,697 distinct (species_symbol, name,
value) triples -- 37,175 rows (18.5%) were pure duplicates, and this was
already live and visible in the species detail Characteristics section,
not just a wizard-building artifact.

Keeps exactly one row per distinct (species_symbol, name, value) --
the lowest `id`, so this is deterministic and re-runnable. Idempotent:
a second run finds nothing left to delete.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    before = conn.execute("SELECT COUNT(*) FROM characteristics").fetchone()[0]

    conn.execute(
        """
        DELETE FROM characteristics
        WHERE id NOT IN (
            SELECT MIN(id) FROM characteristics
            GROUP BY species_symbol, name, value
        )
        """
    )
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM characteristics").fetchone()[0]
    print(f"characteristics rows: {before} -> {after} ({before - after} duplicate rows removed)")
    conn.close()


if __name__ == "__main__":
    main()
