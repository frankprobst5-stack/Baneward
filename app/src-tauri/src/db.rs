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
//! Safety rule enforced here, not just in the UI (see README.md): a tag
//! is always inserted with `verified = 0`. The only way one becomes
//! verified is the separate `verify_tag` command — a deliberate human
//! action, never a side effect of adding one.

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
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            species_symbol TEXT NOT NULL REFERENCES species(symbol),
            tag_type TEXT NOT NULL CHECK(tag_type IN ('medical','poisonous','edible','useful')),
            value TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            added_by TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_species_sciname ON species(scientific_name);
        CREATE INDEX IF NOT EXISTS idx_species_common ON species(common_name);
        CREATE INDEX IF NOT EXISTS idx_images_species ON images(species_symbol);
        CREATE INDEX IF NOT EXISTS idx_tags_species ON tags(species_symbol);
        ",
    )
    .expect("failed to ensure schema");
}
