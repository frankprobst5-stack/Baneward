#!/usr/bin/env python3
"""Ingests Dr. Duke's Phytochemical and Ethnobotanical Database's real
ETHNOBOT table (USDA ARS, CC0 -- https://catalog.data.gov/dataset/
dr-dukes-phytochemical-and-ethnobotanical-databases) as `claims` rows.

Scope, deliberately: ETHNOBOT only. It's the one table that's directly
species-level (genus/species columns, no resolution through Duke's own
internal plant-ID numbering needed) and the real match-rate against our
own species was tested before writing this script: 62.2% of its 82,873
rows match a species we already have. The chemical-level tables
(ACTIVITIES, AGGREGAC, CHEMICALS, CHEM_MEANS, FARMACY_NEW, DOSAGE) need
a species resolution step through FNFTAX.csv first and are real,
separate future work, not done here.

Every claim here is category='medical' (Duke's own activities are
documented traditional/ethnobotanical uses, not food or poison claims
specifically) and evidence_type='traditional' (a documented historical
use, explicitly not the same evidence class as a laboratory finding or
a clinical trial). Inserted unverified, same as every other claim --
being CC0 government data doesn't exempt it from the same human review
before it counts as confirmed.
"""
import csv
import sqlite3
from pathlib import Path

RAW = Path(__file__).parent / "raw"
DUKE = RAW / "duke"
DB_PATH = Path(__file__).parent / "baneward.db"
SOURCE_LABEL = "Dr. Duke's Phytochemical and Ethnobotanical Databases (USDA ARS, CC0)"


def load_references():
    """REFERENCE short code -> real long-form citation, where available."""
    refs = {}
    with open(DUKE / "REFERENCES.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            refs[row["REFERENCE"]] = row.get("LONGREF") or row["REFERENCE"]
    return refs


def load_species_lookup(conn):
    """(genus, species) -> our accepted symbol, covering both direct
    species names and resolved synonyms -- this is exactly the real,
    already-ingested synonym table (Phase 1.5) earning its keep."""
    lookup = {}
    for symbol, sci_name in conn.execute("SELECT symbol, scientific_name FROM species"):
        parts = sci_name.split()
        if len(parts) >= 2:
            lookup[(parts[0], parts[1].rstrip("."))] = symbol
    for accepted_symbol, sci_name in conn.execute(
        "SELECT accepted_symbol, scientific_name FROM synonyms"
    ):
        parts = sci_name.split()
        if len(parts) >= 2:
            lookup.setdefault((parts[0], parts[1].rstrip(".")), accepted_symbol)
    return lookup


def main():
    conn = sqlite3.connect(DB_PATH)

    references = load_references()
    print(f"{len(references)} reference citations loaded")

    species_lookup = load_species_lookup(conn)
    print(f"{len(species_lookup)} (genus, species) pairs resolvable to our own species")

    conn.execute(
        "DELETE FROM claims WHERE source = ?", (SOURCE_LABEL,)
    )  # idempotent re-run

    inserted = 0
    skipped_no_match = 0
    rows_to_insert = []
    with open(DUKE / "ETHNOBOT.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            pair = (row["GENUS"], row["SPECIES"])
            symbol = species_lookup.get(pair)
            if not symbol:
                skipped_no_match += 1
                continue

            activity = (row.get("ACTIVITY") or "").strip()
            if not activity:
                continue

            region = (row.get("COUNTRY") or "").strip() or None
            ref_code = (row.get("REFERENCE") or "").strip()
            reference = references.get(ref_code, ref_code) if ref_code else None

            rows_to_insert.append(
                (
                    symbol,
                    "medical",
                    f"Traditional/ethnobotanical use: {activity}",
                    "traditional",
                    SOURCE_LABEL,
                    reference,
                    region,
                    "duke-ethnobot-ingest",
                )
            )
            inserted += 1

    conn.executemany(
        """INSERT INTO claims
           (species_symbol, category, description, evidence_type, source, reference, region, added_by)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows_to_insert,
    )
    conn.commit()
    conn.close()

    print(f"Inserted {inserted} real ethnobotanical claims (unverified, as always)")
    print(f"Skipped {skipped_no_match} rows -- species not in our own US database (Duke's data is global)")


if __name__ == "__main__":
    main()
