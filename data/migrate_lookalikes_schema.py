#!/usr/bin/env python3
"""Creates the real `lookalike_pairs` / `lookalike_differentiators` tables
on the master database (db.rs's own `ensure_schema` only runs against a
fresh dev database, not the real working one). Idempotent: `CREATE TABLE
IF NOT EXISTS`, safe to re-run.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lookalike_pairs (
    id INTEGER PRIMARY KEY,
    species_a_symbol TEXT NOT NULL REFERENCES species(symbol),
    species_b_symbol TEXT NOT NULL REFERENCES species(symbol),
    risk_level TEXT NOT NULL CHECK(risk_level IN ('fatal','severe','moderate','mild')),
    summary TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    added_by TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    verified_by TEXT,
    verified_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_lookalike_pairs_a ON lookalike_pairs(species_a_symbol);
CREATE INDEX IF NOT EXISTS idx_lookalike_pairs_b ON lookalike_pairs(species_b_symbol);

CREATE TABLE IF NOT EXISTS lookalike_differentiators (
    id INTEGER PRIMARY KEY,
    pair_id INTEGER NOT NULL REFERENCES lookalike_pairs(id),
    characteristic TEXT NOT NULL,
    species_a_value TEXT NOT NULL,
    species_b_value TEXT NOT NULL,
    reliability_notes TEXT,
    source TEXT,
    verified INTEGER NOT NULL DEFAULT 0,
    added_by TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    verified_by TEXT,
    verified_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_lookalike_diff_pair ON lookalike_differentiators(pair_id);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("lookalike_pairs / lookalike_differentiators tables ready")


if __name__ == "__main__":
    main()
