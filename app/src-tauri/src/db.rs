//! Local SQLite store.
//!
//! The real data (35,326 US species from USDA PLANTS — see
//! `data/ingest_full.py` at the repo root) ships bundled inside the app
//! (`resources/baneward.db`) and gets copied into the real per-OS app
//! data directory on first run only. Every launch after that opens the
//! user's own live copy, so their own tag edits persist across app
//! updates instead of being silently overwritten by a newer bundled
//! resource.
//!
//! Safety rule enforced here, not just in the UI (see README.md): a claim
//! is always inserted with `verified = 0`. The only way one becomes
//! verified is the separate `verify_claim` command — a deliberate human
//! action, never a side effect of adding one.
//!
//! `claims` (redesigned 2026-10-29, was the simpler `tags` table) keeps
//! two real axes separate rather than conflating them, per real feedback
//! that merging "what domain is this about" with "how do we know it" was
//! a mistake: `category` is what the claim is about (medical/poisonous/
//! edible/useful — unchanged from `tags`, Baneward's own red-alert logic
//! still keys off this), `evidence_type` is how the claim was arrived at
//! (traditional use, laboratory finding, animal study, human clinical
//! trial, regulatory source, or unspecified). A chemical's reported
//! toxicity in a lab assay is not the same kind of claim as a documented
//! human poisoning case, even if both end up tagged `category='poisonous'`
//! — `evidence_type` is what lets Baneward (and a reader) tell them apart
//! without losing the category-based red-alert filtering.

use rusqlite::Connection;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, Manager};

pub struct Db(pub Mutex<Connection>);

/// Overridable via BANEWARD_DATA_DIR for dev/testing against a throwaway
/// database instead of the real per-OS app data directory.
pub fn data_dir() -> PathBuf {
    let dir = match std::env::var("BANEWARD_DATA_DIR") {
        Ok(dir) => PathBuf::from(dir),
        Err(_) => dirs::data_dir().unwrap_or_else(std::env::temp_dir).join("baneward"),
    };
    std::fs::create_dir_all(&dir).expect("failed to create app data directory");
    dir
}

pub fn open(app: &AppHandle) -> Connection {
    let path = data_dir().join("baneward.db");
    if !path.exists() {
        let bundled = app
            .path()
            .resolve("resources/baneward.db", tauri::path::BaseDirectory::Resource)
            .expect("bundled baneward.db resource missing from the app bundle");
        std::fs::copy(&bundled, &path).unwrap_or_else(|e| {
            panic!(
                "failed to seed the real database from the bundled resource on first run: {e}"
            )
        });
    }
    let conn = Connection::open(&path).expect("failed to open database");
    ensure_schema(&conn);
    conn
}

/// Idempotent. The bundled database already has these tables (built by
/// data/ingest_full.py) — this only matters for a dev database created
/// from scratch (BANEWARD_DATA_DIR pointed somewhere empty) rather than
/// seeded from the bundled resource.
fn ensure_schema(conn: &Connection) {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS species (
            symbol TEXT PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            authorship TEXT,
            common_name TEXT,
            family TEXT,
            duration TEXT,
            growth_habit TEXT,
            native_status TEXT,
            source TEXT DEFAULT 'USDA PLANTS',
            source_url TEXT,
            enriched_at TEXT
        );
        -- `source`/`verified`/`added_by`/`added_at` added for real user-uploaded
        -- photos (data/migrate_images_schema.py) -- same rule as `claims`: an
        -- uploaded image is a claim that a photo shows this species, and it
        -- defaults unverified for exactly the same reason a text claim does.
        -- Existing USDA PLANTS rows default source='usda_plants', verified=1 --
        -- that's institutional data already tied to the right species by USDA's
        -- own curation, not a new identification claim someone just made.
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            usda_image_id INTEGER,
            url TEXT NOT NULL,
            is_public_domain INTEGER NOT NULL,
            photographer TEXT,
            institution TEXT,
            source TEXT NOT NULL DEFAULT 'usda_plants',
            verified INTEGER NOT NULL DEFAULT 1,
            added_by TEXT,
            added_at TEXT,
            verified_by TEXT,
            verified_at TEXT
        );
        -- Replaces the old `tags` table (migrated by
        -- data/migrate_claims_schema.py, not recreated from scratch --
        -- this CREATE only matters for a dev db built from nothing).
        CREATE TABLE IF NOT EXISTS claims (
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
        CREATE INDEX IF NOT EXISTS idx_species_sciname ON species(scientific_name);
        CREATE INDEX IF NOT EXISTS idx_species_common ON species(common_name);
        CREATE INDEX IF NOT EXISTS idx_images_species ON images(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_claims_species ON claims(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_claims_category ON claims(category);

        -- Real scientific-name synonyms (data/ingest_characteristics_and_synonyms.py)
        -- so an older/alternate Latin name still finds the current accepted species.
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            accepted_symbol TEXT NOT NULL REFERENCES species(symbol),
            scientific_name TEXT NOT NULL,
            authorship TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_synonyms_sciname ON synonyms(scientific_name);
        CREATE INDEX IF NOT EXISTS idx_synonyms_accepted ON synonyms(accepted_symbol);

        -- Real USDA PlantCharacteristics data -- only ~5.8% of species have
        -- any (confirmed, not assumed universal); a missing row here means
        -- genuinely undocumented, not false.
        CREATE TABLE IF NOT EXISTS characteristics (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            name TEXT NOT NULL,
            value TEXT,
            category TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_characteristics_species ON characteristics(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_characteristics_name_value ON characteristics(name, value);

        -- Real state/county-level distribution data (data/ingest_distribution.py),
        -- from a separate NRCS ArcGIS service, not the bundled USDA PLANTS
        -- package itself. Real coverage isn't universal -- a 150-species
        -- prototype found 27%/34% of species have no state/county record at
        -- all in this service. The UNIQUE index exists because the source
        -- service's own county-level rows had real duplicates (28.8% of raw
        -- rows in the same prototype) -- enforced here so that bug can't
        -- quietly reappear on a future re-ingest. nativity_status is derived
        -- from the source's own numeric plant_nativity_id code, cross-checked
        -- against species.native_status on 26,913 real rows before trusting
        -- it: code 5 = native, codes 3 and 7 both = introduced (the exact
        -- difference between 3 and 7 isn't resolved yet, both stored as
        -- 'introduced' for now). idx_distribution_subdivision exists for the
        -- real, still-unbuilt click-a-region-see-what-lives-there lookup.
        CREATE TABLE IF NOT EXISTS distribution (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            level TEXT NOT NULL CHECK(level IN ('state','county')),
            subdivision_name TEXT NOT NULL,
            nativity_status TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_distribution_unique ON distribution(species_symbol, level, subdivision_name);
        CREATE INDEX IF NOT EXISTS idx_distribution_subdivision ON distribution(subdivision_name);

        -- Real Dr. Duke phytochemistry data (data/ingest_duke_phytochemistry.py),
        -- normalized on purpose -- a first attempt stored one claims row per
        -- (species, chemical, bioactivity) triple and produced 983,790 rows
        -- (336MB) by duplicating each chemical's whole bioactivity profile on
        -- every one of the hundreds of species that happen to contain it.
        -- Real fix: a chemical's bioactivities are a fact about the chemical,
        -- not about any one species -- store them once.
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
        -- Real tested distribution before building the UI around it: max 221
        -- distinct chemicals for one species, median 15 -- not the 8,460-row
        -- mess the first attempt produced.
        CREATE TABLE IF NOT EXISTS species_chemicals (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            chemical_id INTEGER NOT NULL REFERENCES chemicals(id),
            plant_part TEXT,
            source TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_species_chemicals_species ON species_chemicals(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_species_chemicals_chem ON species_chemicals(chemical_id);

        -- Curated dangerous-lookalike comparisons (v2, 2026-11), per real
        -- outside-review feedback: deliberately a reviewed registry of
        -- specific pairs, not an auto-generated 'similar species' feature
        -- (the data model itself guards against that -- there's no
        -- similarity score here, just a pair someone explicitly entered
        -- and sourced). Same unverified-by-default rule as claims and
        -- images: a pair or a single differentiator within it can be
        -- entered by anyone, but only counts as reviewed once a human
        -- explicitly verifies it. A verified pair does NOT imply every
        -- differentiator under it is independently verified -- each one
        -- tracks its own review status, because one bad entry (a wrong
        -- height range, a stem-color claim that doesn't hold up) shouldn't
        -- hide inside an otherwise-solid pair.
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

        -- v2's fourth real deliverable (2026-11): a user's own sighting, not
        -- an editorial claim -- deliberately has no `verified` column at
        -- all, unlike every other user-contributed table in this file. A
        -- field note is a personal record, not a fact being proposed for
        -- review; the one thing it must never become is a quiet stand-in
        -- for a confirmed identification, so get_species keeps it in its
        -- own section, never merged into claims. species_symbol is
        -- nullable on purpose -- a note can exist before anyone knows what
        -- the plant actually is.
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
        ",
    )
    .expect("failed to ensure schema");
}
