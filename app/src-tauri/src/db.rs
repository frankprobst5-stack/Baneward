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
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            usda_image_id INTEGER,
            url TEXT NOT NULL,
            is_public_domain INTEGER NOT NULL,
            photographer TEXT,
            institution TEXT
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
        ",
    )
    .expect("failed to ensure schema");
}
