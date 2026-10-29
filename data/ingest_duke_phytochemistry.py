#!/usr/bin/env python3
"""Ingests Dr. Duke's real chemical/bioactivity data (FARMACY_NEW +
AGGREGAC, resolved through FNFTAX) into three normalized tables:
`chemicals`, `chemical_activities`, `species_chemicals`.

Replaces a first attempt that stored one `claims` row per (species,
chemical, bioactivity) triple -- 983,790 rows, 336MB, one species with
8,460 entries -- by duplicating each chemical's whole bioactivity
profile on every species that happens to contain it. A chemical's
bioactivities are a fact about the chemical, not about any one plant;
storing them once and linking species to chemicals through a lightweight
join table is the real fix, not a smaller version of the same mistake.

Same safety framing as before, now expressed structurally rather than
in prose: `chemical_activities` carries no category field at all (no
medical/poisonous/edible/useful label gets attached to a raw chemical
finding), and nothing here touches the `claims` table or its
verified-by-default-false rule. A documented bioactivity is browsable
reference data, not a claim about whether any given plant is safe.

Chain, same as before: FNFTAX (FNFNUM -> genus/species) -> FARMACY_NEW
(FNFNUM -> CHEM, plant part) -> AGGREGAC (CHEM -> ACTIVITY, DOSAGE,
REFERENCE). Real tested distribution before building the UI around it:
1,371 of our species resolve through FNFTAX; max 221 distinct chemicals
for one species, median 15.
"""
import csv
import sqlite3
from pathlib import Path

RAW = Path(__file__).parent / "raw"
DUKE = RAW / "duke"
DB_PATH = Path(__file__).parent / "baneward.db"
SOURCE_LABEL = "Dr. Duke's Phytochemical and Ethnobotanical Databases (USDA ARS, CC0)"


def load_species_lookup(conn):
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


def load_fnftax_to_symbol(species_lookup):
    out = {}
    with open(DUKE / "FNFTAX.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            pair = (row["GENUS"], row["SPECIES"])
            symbol = species_lookup.get(pair)
            if symbol:
                out[row["FNFNUM"]] = symbol
    return out


def load_parts():
    parts = {}
    with open(DUKE / "PARTS.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            parts[row["PPCO"]] = row["PPNA"]
    return parts


def load_activities_by_chem():
    out = {}
    with open(DUKE / "AGGREGAC.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            chem = row["CHEM"]
            activity = (row.get("ACTIVITY") or "").strip()
            if not activity:
                continue
            out.setdefault(chem, []).append(
                (activity, (row.get("DOSAGE") or "").strip(), (row.get("REFERENCE") or "").strip())
            )
    return out


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chemicals (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS chemical_activities (
            id INTEGER PRIMARY KEY,
            chemical_id INTEGER NOT NULL REFERENCES chemicals(id),
            activity TEXT NOT NULL,
            dosage TEXT,
            reference TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_chemical_activities_chem ON chemical_activities(chemical_id);
        CREATE TABLE IF NOT EXISTS species_chemicals (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            chemical_id INTEGER NOT NULL REFERENCES chemicals(id),
            plant_part TEXT,
            source TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_species_chemicals_species ON species_chemicals(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_species_chemicals_chem ON species_chemicals(chemical_id);
        """
    )
    # Idempotent re-run: wipe and rebuild all three, they're fully derived.
    conn.executescript(
        "DELETE FROM species_chemicals; DELETE FROM chemical_activities; DELETE FROM chemicals;"
    )

    species_lookup = load_species_lookup(conn)
    fnf_to_symbol = load_fnftax_to_symbol(species_lookup)
    print(f"{len(fnf_to_symbol)} FNFTAX entries resolve to our own species")

    parts = load_parts()
    activities_by_chem = load_activities_by_chem()
    print(f"{len(activities_by_chem)} distinct chemicals with real documented bioactivities")

    # Pass 1: find which chemicals actually matter (present in a matched
    # species AND have real bioactivity data), insert each exactly once.
    chem_ids = {}
    species_chem_rows = []  # (species_symbol, chem_name, plant_part)
    skipped_no_species = 0
    skipped_no_activity = 0
    with open(DUKE / "FARMACY_NEW.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            symbol = fnf_to_symbol.get(row["FNFNUM"])
            if not symbol:
                skipped_no_species += 1
                continue
            chem = row["CHEM"]
            if chem not in activities_by_chem:
                skipped_no_activity += 1
                continue
            plant_part = parts.get(row.get("PPCO", "")) or None
            species_chem_rows.append((symbol, chem, plant_part))

    print(f"{skipped_no_species} FARMACY_NEW rows skipped -- species not in our own US database")
    print(f"{skipped_no_activity} FARMACY_NEW rows skipped -- chemical has no documented bioactivity")

    distinct_chems = {chem for _, chem, _ in species_chem_rows}
    conn.executemany(
        "INSERT INTO chemicals (name) VALUES (?)", [(c,) for c in sorted(distinct_chems)]
    )
    conn.commit()
    for row in conn.execute("SELECT id, name FROM chemicals"):
        chem_ids[row[1]] = row[0]
    print(f"{len(chem_ids)} distinct chemicals inserted (each once, not per-species)")

    activity_rows = []
    for chem in distinct_chems:
        cid = chem_ids[chem]
        for activity, dosage, ref in activities_by_chem[chem]:
            activity_rows.append((cid, activity, dosage or None, ref or None))
    conn.executemany(
        "INSERT INTO chemical_activities (chemical_id, activity, dosage, reference) VALUES (?,?,?,?)",
        activity_rows,
    )
    print(f"{len(activity_rows)} chemical-activity rows inserted (each once, not per-species)")

    link_rows = [
        (symbol, chem_ids[chem], plant_part, SOURCE_LABEL)
        for symbol, chem, plant_part in species_chem_rows
    ]
    conn.executemany(
        "INSERT INTO species_chemicals (species_symbol, chemical_id, plant_part, source) VALUES (?,?,?,?)",
        link_rows,
    )
    print(f"{len(link_rows)} species-chemical links inserted")

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
