//! Tauri commands — the real search/browse/edit surface over the local
//! database. The one rule every write path here follows (see README.md):
//! `add_claim` always inserts unverified; nothing here can make a claim
//! appear verified except the separate, deliberate `verify_claim` call.

use crate::db::Db;
use base64::Engine;
use rusqlite::params;
use serde::{Deserialize, Serialize};
use tauri::State;

#[derive(Serialize)]
pub struct SpeciesSummary {
    pub symbol: String,
    pub scientific_name: String,
    pub common_name: Option<String>,
    pub family: Option<String>,
    pub has_poisonous_claim: bool,
    /// Why this result matched — "common_name" | "scientific_name" | "synonym".
    /// A synonym match means the query hit an older/alternate Latin name; the
    /// rest of the row is still the real, current accepted species, never the
    /// synonym's own (sometimes outdated) data.
    pub matched_via: String,
    /// Set only when matched_via == "synonym" — the actual old name that matched,
    /// so the UI can show "matched via <old name>" instead of looking wrong.
    pub matched_synonym: Option<String>,
}

#[tauri::command]
pub fn search_species(db: State<Db>, query: String) -> Result<Vec<SpeciesSummary>, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let like = format!("%{}%", query.trim());

    // Direct matches (common or scientific name) ranked above synonym
    // matches, common-name hits ranked above scientific-name hits within
    // that. A species that matches both directly and via an old synonym
    // name only needs the direct row -- the dedup pass below keeps the
    // first (highest-ranked) occurrence per symbol.
    let mut stmt = conn
        .prepare(
            "SELECT s.symbol, s.scientific_name, s.common_name, s.family,
                    EXISTS(SELECT 1 FROM claims c WHERE c.species_symbol = s.symbol
                           AND c.category = 'poisonous' AND c.verified = 1) AS has_poisonous_claim,
                    CASE WHEN s.common_name LIKE ?1 THEN 'common_name' ELSE 'scientific_name' END AS matched_via,
                    NULL AS matched_synonym,
                    0 AS rank
             FROM species s
             WHERE s.scientific_name LIKE ?1 OR s.common_name LIKE ?1

             UNION ALL

             SELECT s.symbol, s.scientific_name, s.common_name, s.family,
                    EXISTS(SELECT 1 FROM claims c WHERE c.species_symbol = s.symbol
                           AND c.category = 'poisonous' AND c.verified = 1) AS has_poisonous_claim,
                    'synonym' AS matched_via,
                    syn.scientific_name AS matched_synonym,
                    1 AS rank
             FROM synonyms syn
             JOIN species s ON s.symbol = syn.accepted_symbol
             WHERE syn.scientific_name LIKE ?1

             ORDER BY rank, common_name, scientific_name
             LIMIT 200",
        )
        .map_err(|e| e.to_string())?;

    let rows = stmt
        .query_map(params![like], |row| {
            Ok(SpeciesSummary {
                symbol: row.get(0)?,
                scientific_name: row.get(1)?,
                common_name: row.get(2)?,
                family: row.get(3)?,
                has_poisonous_claim: row.get(4)?,
                matched_via: row.get(5)?,
                matched_synonym: row.get(6)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    // Dedup by symbol, keeping the first (best-ranked) occurrence, then cap
    // at 50 real results for the UI.
    let mut seen = std::collections::HashSet::new();
    Ok(rows
        .into_iter()
        .filter(|r| seen.insert(r.symbol.clone()))
        .take(50)
        .collect())
}

#[derive(Serialize)]
pub struct ImageInfo {
    pub id: i64,
    pub url: String,
    pub is_public_domain: bool,
    pub photographer: Option<String>,
    pub institution: Option<String>,
    /// 'usda_plants' for everything from the original ingest, 'user_upload'
    /// for a photo someone added through the app, 'inaturalist' for a
    /// cached community (research-grade, CC0/CC-BY) photo.
    pub source: String,
    /// User uploads and iNaturalist photos start false, same rule as a
    /// claim -- see `add_user_image` and data/ingest_inaturalist_images.py.
    /// USDA rows are true by default (institutional data, not a new claim).
    pub verified: bool,
    pub added_by: Option<String>,
    pub added_at: Option<String>,
    /// Set when the actual bytes are cached in the db (iNaturalist images;
    /// a future user-upload migration could use this too) -- a data URI
    /// the frontend can use directly, no live network fetch needed. None
    /// for USDA's plain-URL rows and for user uploads (which still go
    /// through `read_image_bytes` against their local file).
    pub data_base64: Option<String>,
}

#[derive(Serialize)]
pub struct ClaimInfo {
    pub id: i64,
    pub category: String,
    pub plant_part: Option<String>,
    pub description: String,
    pub evidence_type: String,
    pub verified: bool,
    pub source: Option<String>,
    pub reference: Option<String>,
    pub region: Option<String>,
    pub added_by: Option<String>,
    pub added_at: String,
    pub verified_by: Option<String>,
    pub verified_at: Option<String>,
}

#[derive(Serialize)]
pub struct CharacteristicInfo {
    pub name: String,
    pub value: Option<String>,
    pub category: Option<String>,
}

#[derive(Serialize)]
pub struct ActivityInfo {
    pub activity: String,
    pub dosage: Option<String>,
    pub reference: Option<String>,
}

#[derive(Serialize)]
pub struct ChemicalInfo {
    pub name: String,
    pub plant_part: Option<String>,
    /// Real documented bioactivities (Dr. Duke's AGGREGAC) — stored once
    /// per chemical, not duplicated per species (see
    /// data/ingest_duke_phytochemistry.py's own notes on why the first
    /// attempt at this produced 983,790 rows instead of ~19,000). Raw
    /// chemical/laboratory findings, not a safety or therapeutic claim —
    /// deliberately kept separate from the `claims` table.
    pub activities: Vec<ActivityInfo>,
}

#[derive(Serialize)]
pub struct LookalikeSummary {
    pub pair_id: i64,
    pub other_symbol: String,
    pub other_common_name: Option<String>,
    pub other_scientific_name: String,
    pub risk_level: String,
    pub summary: String,
    pub verified: bool,
}

#[derive(Serialize)]
pub struct SpeciesDetail {
    pub symbol: String,
    pub scientific_name: String,
    pub authorship: Option<String>,
    pub common_name: Option<String>,
    pub family: Option<String>,
    pub duration: Option<String>,
    pub growth_habit: Option<String>,
    pub native_status: Option<String>,
    pub source_url: Option<String>,
    pub images: Vec<ImageInfo>,
    pub claims: Vec<ClaimInfo>,
    /// Real USDA PlantCharacteristics data — present for only ~5.8% of
    /// species (confirmed, not assumed universal). An empty list means
    /// genuinely undocumented, not "nothing interesting."
    pub characteristics: Vec<CharacteristicInfo>,
    /// Older/alternate scientific names that resolve to this species.
    pub synonyms: Vec<String>,
    /// Real documented chemicals (Dr. Duke), present for ~3.9% of species
    /// (1,371 of 35,326 resolve through Duke's own taxonomy).
    pub chemicals: Vec<ChemicalInfo>,
    /// Curated dangerous-lookalike pairs this species is part of, either
    /// side (v2) — a reviewed registry, never an auto-generated similarity
    /// score. Empty means no pair has been entered yet, not "nothing looks
    /// like this."
    pub lookalikes: Vec<LookalikeSummary>,
}

#[tauri::command]
pub fn get_species(db: State<Db>, symbol: String) -> Result<SpeciesDetail, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;

    let mut species = conn
        .query_row(
            "SELECT symbol, scientific_name, authorship, common_name, family,
                    duration, growth_habit, native_status, source_url
             FROM species WHERE symbol = ?1",
            params![symbol],
            |row| {
                Ok(SpeciesDetail {
                    symbol: row.get(0)?,
                    scientific_name: row.get(1)?,
                    authorship: row.get(2)?,
                    common_name: row.get(3)?,
                    family: row.get(4)?,
                    duration: row.get(5)?,
                    growth_habit: row.get(6)?,
                    native_status: row.get(7)?,
                    source_url: row.get(8)?,
                    images: Vec::new(),
                    claims: Vec::new(),
                    characteristics: Vec::new(),
                    synonyms: Vec::new(),
                    chemicals: Vec::new(),
                    lookalikes: Vec::new(),
                })
            },
        )
        .map_err(|e| format!("species not found: {e}"))?;

    let mut img_stmt = conn
        .prepare(
            "SELECT id, url, is_public_domain, photographer, institution,
                    source, verified, added_by, added_at, data
             FROM images WHERE species_symbol = ?1
             ORDER BY is_public_domain DESC, added_at DESC",
        )
        .map_err(|e| e.to_string())?;
    species.images = img_stmt
        .query_map(params![species.symbol], |row| {
            let url: String = row.get(1)?;
            let blob: Option<Vec<u8>> = row.get(9)?;
            let ext = std::path::Path::new(&url)
                .extension()
                .and_then(|e| e.to_str())
                .map(|e| e.to_lowercase())
                .unwrap_or_default();
            let data_base64 = blob.map(|bytes| {
                format!(
                    "data:{};base64,{}",
                    image_mime_type(&ext),
                    base64::engine::general_purpose::STANDARD.encode(bytes)
                )
            });
            Ok(ImageInfo {
                id: row.get(0)?,
                url,
                is_public_domain: row.get(2)?,
                photographer: row.get(3)?,
                institution: row.get(4)?,
                source: row.get(5)?,
                verified: row.get(6)?,
                added_by: row.get(7)?,
                added_at: row.get(8)?,
                data_base64,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let mut claim_stmt = conn
        .prepare(
            "SELECT id, category, plant_part, description, evidence_type, verified,
                    source, reference, region, added_by, added_at, verified_by, verified_at
             FROM claims WHERE species_symbol = ?1 ORDER BY verified DESC, added_at DESC",
        )
        .map_err(|e| e.to_string())?;
    species.claims = claim_stmt
        .query_map(params![species.symbol], |row| {
            Ok(ClaimInfo {
                id: row.get(0)?,
                category: row.get(1)?,
                plant_part: row.get(2)?,
                description: row.get(3)?,
                evidence_type: row.get(4)?,
                verified: row.get(5)?,
                source: row.get(6)?,
                reference: row.get(7)?,
                region: row.get(8)?,
                added_by: row.get(9)?,
                added_at: row.get(10)?,
                verified_by: row.get(11)?,
                verified_at: row.get(12)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let mut char_stmt = conn
        .prepare(
            "SELECT name, value, category FROM characteristics
             WHERE species_symbol = ?1 ORDER BY category, name",
        )
        .map_err(|e| e.to_string())?;
    species.characteristics = char_stmt
        .query_map(params![species.symbol], |row| {
            Ok(CharacteristicInfo {
                name: row.get(0)?,
                value: row.get(1)?,
                category: row.get(2)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let mut syn_stmt = conn
        .prepare(
            "SELECT scientific_name FROM synonyms
             WHERE accepted_symbol = ?1 ORDER BY scientific_name",
        )
        .map_err(|e| e.to_string())?;
    species.synonyms = syn_stmt
        .query_map(params![species.symbol], |row| row.get::<_, String>(0))
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    // One flat query (chemical x activity), grouped into ChemicalInfo in
    // Rust -- cheaper than N+1 queries per chemical, and at a real max of
    // 221 distinct chemicals for one species this is a small result set.
    let mut chem_stmt = conn
        .prepare(
            "SELECT ch.name, sc.plant_part, ca.activity, ca.dosage, ca.reference
             FROM species_chemicals sc
             JOIN chemicals ch ON ch.id = sc.chemical_id
             LEFT JOIN chemical_activities ca ON ca.chemical_id = ch.id
             WHERE sc.species_symbol = ?1
             ORDER BY ch.name, ca.activity",
        )
        .map_err(|e| e.to_string())?;
    let chem_rows = chem_stmt
        .query_map(params![species.symbol], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, Option<String>>(1)?,
                row.get::<_, Option<String>>(2)?,
                row.get::<_, Option<String>>(3)?,
                row.get::<_, Option<String>>(4)?,
            ))
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let mut chem_order: Vec<String> = Vec::new();
    let mut chem_map: std::collections::HashMap<String, ChemicalInfo> = std::collections::HashMap::new();
    for (name, plant_part, activity, dosage, reference) in chem_rows {
        let entry = chem_map.entry(name.clone()).or_insert_with(|| {
            chem_order.push(name.clone());
            ChemicalInfo {
                name,
                plant_part,
                activities: Vec::new(),
            }
        });
        if let Some(activity) = activity {
            entry.activities.push(ActivityInfo {
                activity,
                dosage,
                reference,
            });
        }
    }
    species.chemicals = chem_order
        .into_iter()
        .map(|name| chem_map.remove(&name).unwrap())
        .collect();

    let mut look_stmt = conn
        .prepare(
            "SELECT lp.id, lp.risk_level, lp.summary, lp.verified,
                    os.symbol, os.common_name, os.scientific_name
             FROM lookalike_pairs lp
             JOIN species os ON os.symbol = (
                 CASE WHEN lp.species_a_symbol = ?1 THEN lp.species_b_symbol ELSE lp.species_a_symbol END
             )
             WHERE lp.species_a_symbol = ?1 OR lp.species_b_symbol = ?1
             ORDER BY lp.verified DESC, lp.id",
        )
        .map_err(|e| e.to_string())?;
    species.lookalikes = look_stmt
        .query_map(params![species.symbol], |row| {
            Ok(LookalikeSummary {
                pair_id: row.get(0)?,
                risk_level: row.get(1)?,
                summary: row.get(2)?,
                verified: row.get(3)?,
                other_symbol: row.get(4)?,
                other_common_name: row.get(5)?,
                other_scientific_name: row.get(6)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    Ok(species)
}

const VALID_CATEGORIES: [&str; 4] = ["medical", "poisonous", "edible", "useful"];
const VALID_EVIDENCE_TYPES: [&str; 6] = [
    "traditional",
    "laboratory",
    "animal_study",
    "human_clinical",
    "regulatory",
    "unspecified",
];

/// Always inserts unverified (verified = 0). This is the one rule in the
/// whole app that must never bend: adding a claim is never, by itself,
/// enough to make it appear confirmed.
#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub fn add_claim(
    db: State<Db>,
    symbol: String,
    category: String,
    description: String,
    plant_part: Option<String>,
    evidence_type: Option<String>,
    source: Option<String>,
    reference: Option<String>,
    region: Option<String>,
    added_by: Option<String>,
) -> Result<i64, String> {
    if !VALID_CATEGORIES.contains(&category.as_str()) {
        return Err(format!(
            "invalid category '{category}', must be one of {VALID_CATEGORIES:?}"
        ));
    }
    if description.trim().is_empty() {
        return Err("claim description can't be empty".into());
    }
    let evidence_type = evidence_type.unwrap_or_else(|| "unspecified".to_string());
    if !VALID_EVIDENCE_TYPES.contains(&evidence_type.as_str()) {
        return Err(format!(
            "invalid evidence_type '{evidence_type}', must be one of {VALID_EVIDENCE_TYPES:?}"
        ));
    }

    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO claims
            (species_symbol, category, plant_part, description, evidence_type,
             verified, source, reference, region, added_by)
         VALUES (?1, ?2, ?3, ?4, ?5, 0, ?6, ?7, ?8, ?9)",
        params![
            symbol,
            category,
            plant_part,
            description.trim(),
            evidence_type,
            source,
            reference,
            region,
            added_by
        ],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

/// The only path by which a claim becomes verified — a separate, explicit
/// call, never a side effect of add_claim or an edit.
#[tauri::command]
pub fn verify_claim(db: State<Db>, claim_id: i64, verified_by: Option<String>) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let changed = conn
        .execute(
            "UPDATE claims SET verified = 1, verified_by = ?2, verified_at = datetime('now')
             WHERE id = ?1",
            params![claim_id, verified_by],
        )
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err(format!("no claim with id {claim_id}"));
    }
    Ok(())
}

#[tauri::command]
pub fn delete_claim(db: State<Db>, claim_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM claims WHERE id = ?1", params![claim_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

const VALID_IMAGE_EXTENSIONS: [&str; 5] = ["jpg", "jpeg", "png", "webp", "gif"];

fn image_mime_type(ext: &str) -> &'static str {
    match ext {
        "png" => "image/png",
        "webp" => "image/webp",
        "gif" => "image/gif",
        _ => "image/jpeg",
    }
}

/// User-uploaded images only ever live under here -- enforced in both
/// `add_user_image` (where they get copied to) and `read_image_bytes` (so
/// that command can't be made to read an arbitrary path off disk).
fn user_images_dir() -> std::path::PathBuf {
    crate::db::data_dir().join("user_images")
}

fn is_under_user_images_dir(path: &std::path::Path) -> bool {
    let base = user_images_dir();
    match (path.canonicalize(), base.canonicalize()) {
        (Ok(p), Ok(b)) => p.starts_with(b),
        _ => false,
    }
}

/// Lets someone attach their own photo to a species -- the same rule as a
/// text claim (see README.md): always inserted unverified. A user's photo
/// is a claim that this is what the species looks like, not a confirmed
/// fact just because someone uploaded it -- "identification confidence is
/// not safety confidence" applies to a picture exactly as much as a tag.
#[tauri::command]
pub fn add_user_image(
    db: State<Db>,
    symbol: String,
    path: String,
    added_by: Option<String>,
) -> Result<i64, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let exists: bool = conn
        .query_row(
            "SELECT 1 FROM species WHERE symbol = ?1",
            params![symbol],
            |_| Ok(true),
        )
        .unwrap_or(false);
    if !exists {
        return Err(format!("no species with symbol {symbol}"));
    }

    let src_path = std::path::Path::new(&path);
    let ext = src_path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase())
        .unwrap_or_default();
    if !VALID_IMAGE_EXTENSIONS.contains(&ext.as_str()) {
        return Err(format!(
            "unsupported image type '.{ext}' -- use one of {VALID_IMAGE_EXTENSIONS:?}"
        ));
    }

    let dest_dir = user_images_dir().join(&symbol);
    std::fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_nanos();
    let dest_path = dest_dir.join(format!("{stamp}.{ext}"));
    std::fs::copy(src_path, &dest_path).map_err(|e| format!("couldn't copy image: {e}"))?;

    conn.execute(
        "INSERT INTO images
            (species_symbol, usda_image_id, url, is_public_domain, photographer,
             institution, source, verified, added_by, added_at)
         VALUES (?1, NULL, ?2, 0, NULL, NULL, 'user_upload', 0, ?3, datetime('now'))",
        params![symbol, dest_path.to_string_lossy(), added_by],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

/// The only path by which a non-institutional photo becomes verified -- a
/// separate, deliberate call, same pattern as `verify_claim`. Covers both
/// a user's own upload and a cached iNaturalist photo (a household member
/// reviewing a research-grade community ID and confirming it); USDA's own
/// images are already institutionally sourced and never go through this.
#[tauri::command]
pub fn verify_user_image(
    db: State<Db>,
    image_id: i64,
    verified_by: Option<String>,
) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let changed = conn
        .execute(
            "UPDATE images SET verified = 1, verified_by = ?2, verified_at = datetime('now')
             WHERE id = ?1 AND source IN ('user_upload', 'inaturalist')",
            params![image_id, verified_by],
        )
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err(format!("no reviewable image with id {image_id}"));
    }
    Ok(())
}

/// Only ever deletes a user's own upload or a cached iNaturalist photo,
/// never a bundled USDA image -- the `source IN (...)` clause is the real
/// enforcement, not just a hidden button in the UI. A user upload's `url`
/// is a real local file path and gets cleaned up; an iNaturalist row's
/// `url` is just the original source link (its bytes live in `data`,
/// removed with the row itself), so there's no local file to unlink.
#[tauri::command]
pub fn delete_user_image(db: State<Db>, image_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let path: String = conn
        .query_row(
            "SELECT url FROM images WHERE id = ?1 AND source IN ('user_upload', 'inaturalist')",
            params![image_id],
            |row| row.get(0),
        )
        .map_err(|_| format!("no reviewable image with id {image_id}"))?;
    conn.execute(
        "DELETE FROM images WHERE id = ?1 AND source IN ('user_upload', 'inaturalist')",
        params![image_id],
    )
    .map_err(|e| e.to_string())?;
    if !path.starts_with("http") {
        let _ = std::fs::remove_file(path); // best-effort cleanup; the db row is the source of truth
    }
    Ok(())
}

/// Reads a local user-uploaded image off disk and returns it as a data URI
/// the frontend can drop straight into an <img src> -- USDA images are
/// plain http(s) URLs already and never go through this. Restricted to
/// `user_images_dir()` so this can't become a general local-file reader
/// callable from the webview.
#[tauri::command]
pub fn read_image_bytes(path: String) -> Result<String, String> {
    let p = std::path::Path::new(&path);
    if !is_under_user_images_dir(p) {
        return Err("refusing to read a path outside the user-images directory".into());
    }
    let ext = p
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase())
        .unwrap_or_default();
    let bytes = std::fs::read(p).map_err(|e| format!("couldn't read image: {e}"))?;
    let encoded = base64::engine::general_purpose::STANDARD.encode(bytes);
    Ok(format!("data:{};base64,{}", image_mime_type(&ext), encoded))
}

/// A real per-source file size cap forced this split (2026-11): GitHub
/// rejected pushing the bundled database once cached community photos
/// (iNaturalist/Wikidata/Smithsonian, Phases 1.9-1.11) pushed it past
/// 2GB -- a hard per-file LFS limit, not the account's overall quota. The
/// bundled installer now ships without these bytes (`data/split_image_packs.py`
/// pulls them into one file per source, each comfortably under the limit on
/// its own); a user who wants the full offline photo set downloads the
/// pack for a source and it gets merged into their own live database here.
/// Real measured sizes as of the split -- update if the packs are
/// regenerated with materially more coverage.
const PACK_SOURCES: [(&str, &str, f64); 3] = [
    (
        "inaturalist",
        "https://media.githubusercontent.com/media/frankprobst5-stack/Baneward/main/data/image_packs/inaturalist.db",
        1950.0,
    ),
    (
        "smithsonian",
        "https://media.githubusercontent.com/media/frankprobst5-stack/Baneward/main/data/image_packs/smithsonian.db",
        783.0,
    ),
    (
        "wikidata_commons",
        "https://media.githubusercontent.com/media/frankprobst5-stack/Baneward/main/data/image_packs/wikidata_commons.db",
        76.0,
    ),
];

#[derive(Serialize)]
pub struct ImagePackStatus {
    pub source: String,
    pub total: i64,
    pub downloaded: i64,
    pub pack_size_mb: f64,
}

#[tauri::command]
pub fn image_pack_status(db: State<Db>) -> Result<Vec<ImagePackStatus>, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    for (source, _url, size_mb) in PACK_SOURCES {
        let total: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM images WHERE source=?1",
                params![source],
                |r| r.get(0),
            )
            .unwrap_or(0);
        let downloaded: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM images WHERE source=?1 AND data IS NOT NULL",
                params![source],
                |r| r.get(0),
            )
            .unwrap_or(0);
        out.push(ImagePackStatus {
            source: source.to_string(),
            total,
            downloaded,
            pack_size_mb: size_mb,
        });
    }
    Ok(out)
}

fn image_packs_dir() -> std::path::PathBuf {
    crate::db::data_dir().join("image_packs")
}

/// Downloads a source's pack file (if not already cached locally) and
/// merges its bytes into the live database -- same ATTACH DATABASE
/// pattern used all session for surgically updating a running app's data.
/// Blocking: a pack can be close to 2GB, so this is meant to be called
/// from the frontend with a "downloading..." state, not expected to
/// return quickly.
#[tauri::command]
pub fn download_image_pack(db: State<Db>, source: String) -> Result<(), String> {
    let (_, url, _) = PACK_SOURCES
        .iter()
        .find(|(s, _, _)| *s == source)
        .ok_or_else(|| format!("unknown image pack source '{source}'"))?;

    let dir = image_packs_dir();
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let pack_path = dir.join(format!("{source}.db"));

    if !pack_path.exists() {
        let tmp_path = dir.join(format!("{source}.db.part"));
        let resp = ureq::get(url)
            .call()
            .map_err(|e| format!("couldn't reach pack server: {e}"))?;
        let mut file = std::fs::File::create(&tmp_path).map_err(|e| e.to_string())?;
        std::io::copy(&mut resp.into_reader(), &mut file).map_err(|e| e.to_string())?;
        drop(file);
        std::fs::rename(&tmp_path, &pack_path).map_err(|e| e.to_string())?;
    }

    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "ATTACH DATABASE ?1 AS pack",
        params![pack_path.to_string_lossy()],
    )
    .map_err(|e| e.to_string())?;
    let result = conn.execute(
        "UPDATE images SET data = (SELECT data FROM pack.pack WHERE pack.pack.id = images.id)
         WHERE source = ?1 AND data IS NULL
           AND EXISTS (SELECT 1 FROM pack.pack WHERE pack.pack.id = images.id)",
        params![source],
    );
    let _ = conn.execute("DETACH DATABASE pack", []);
    result.map_err(|e| e.to_string())?;
    Ok(())
}

const VALID_RISK_LEVELS: [&str; 4] = ["fatal", "severe", "moderate", "mild"];

#[derive(Serialize)]
pub struct LookalikeSpeciesInfo {
    pub symbol: String,
    pub scientific_name: String,
    pub common_name: Option<String>,
    pub family: Option<String>,
}

#[derive(Serialize)]
pub struct DifferentiatorInfo {
    pub id: i64,
    pub characteristic: String,
    pub species_a_value: String,
    pub species_b_value: String,
    pub reliability_notes: Option<String>,
    pub source: Option<String>,
    pub verified: bool,
    pub added_by: Option<String>,
    pub added_at: String,
    pub verified_by: Option<String>,
    pub verified_at: Option<String>,
}

#[derive(Serialize)]
pub struct LookalikePairDetail {
    pub id: i64,
    pub species_a: LookalikeSpeciesInfo,
    pub species_b: LookalikeSpeciesInfo,
    pub risk_level: String,
    pub summary: String,
    pub verified: bool,
    pub added_by: Option<String>,
    pub added_at: String,
    pub verified_by: Option<String>,
    pub verified_at: Option<String>,
    /// Each differentiator carries its own `verified` status independently
    /// of the pair's -- see db.rs's own note on why: a verified pair
    /// shouldn't quietly launder an unreviewed differentiator.
    pub differentiators: Vec<DifferentiatorInfo>,
}

#[tauri::command]
pub fn get_lookalike_pair(db: State<Db>, pair_id: i64) -> Result<LookalikePairDetail, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let mut pair = conn
        .query_row(
            "SELECT lp.id, lp.species_a_symbol, lp.species_b_symbol, lp.risk_level, lp.summary,
                    lp.verified, lp.added_by, lp.added_at, lp.verified_by, lp.verified_at,
                    sa.scientific_name, sa.common_name, sa.family,
                    sb.scientific_name, sb.common_name, sb.family
             FROM lookalike_pairs lp
             JOIN species sa ON sa.symbol = lp.species_a_symbol
             JOIN species sb ON sb.symbol = lp.species_b_symbol
             WHERE lp.id = ?1",
            params![pair_id],
            |row| {
                Ok(LookalikePairDetail {
                    id: row.get(0)?,
                    species_a: LookalikeSpeciesInfo {
                        symbol: row.get(1)?,
                        scientific_name: row.get(10)?,
                        common_name: row.get(11)?,
                        family: row.get(12)?,
                    },
                    species_b: LookalikeSpeciesInfo {
                        symbol: row.get(2)?,
                        scientific_name: row.get(13)?,
                        common_name: row.get(14)?,
                        family: row.get(15)?,
                    },
                    risk_level: row.get(3)?,
                    summary: row.get(4)?,
                    verified: row.get(5)?,
                    added_by: row.get(6)?,
                    added_at: row.get(7)?,
                    verified_by: row.get(8)?,
                    verified_at: row.get(9)?,
                    differentiators: Vec::new(),
                })
            },
        )
        .map_err(|e| format!("lookalike pair not found: {e}"))?;

    let mut stmt = conn
        .prepare(
            "SELECT id, characteristic, species_a_value, species_b_value, reliability_notes,
                    source, verified, added_by, added_at, verified_by, verified_at
             FROM lookalike_differentiators WHERE pair_id = ?1 ORDER BY id",
        )
        .map_err(|e| e.to_string())?;
    pair.differentiators = stmt
        .query_map(params![pair_id], |row| {
            Ok(DifferentiatorInfo {
                id: row.get(0)?,
                characteristic: row.get(1)?,
                species_a_value: row.get(2)?,
                species_b_value: row.get(3)?,
                reliability_notes: row.get(4)?,
                source: row.get(5)?,
                verified: row.get(6)?,
                added_by: row.get(7)?,
                added_at: row.get(8)?,
                verified_by: row.get(9)?,
                verified_at: row.get(10)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    Ok(pair)
}

/// Always inserts unverified -- same rule as `add_claim`. A pair being
/// entered is not the same as a human having reviewed it.
#[tauri::command]
pub fn add_lookalike_pair(
    db: State<Db>,
    species_a_symbol: String,
    species_b_symbol: String,
    risk_level: String,
    summary: String,
    added_by: Option<String>,
) -> Result<i64, String> {
    if !VALID_RISK_LEVELS.contains(&risk_level.as_str()) {
        return Err(format!(
            "invalid risk_level '{risk_level}', must be one of {VALID_RISK_LEVELS:?}"
        ));
    }
    if summary.trim().is_empty() {
        return Err("summary can't be empty".into());
    }
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO lookalike_pairs
            (species_a_symbol, species_b_symbol, risk_level, summary, verified, added_by)
         VALUES (?1, ?2, ?3, ?4, 0, ?5)",
        params![species_a_symbol, species_b_symbol, risk_level, summary.trim(), added_by],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn verify_lookalike_pair(
    db: State<Db>,
    pair_id: i64,
    verified_by: Option<String>,
) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let changed = conn
        .execute(
            "UPDATE lookalike_pairs SET verified = 1, verified_by = ?2, verified_at = datetime('now')
             WHERE id = ?1",
            params![pair_id, verified_by],
        )
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err(format!("no lookalike pair with id {pair_id}"));
    }
    Ok(())
}

#[tauri::command]
pub fn delete_lookalike_pair(db: State<Db>, pair_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "DELETE FROM lookalike_differentiators WHERE pair_id = ?1",
        params![pair_id],
    )
    .map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM lookalike_pairs WHERE id = ?1", params![pair_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Always inserts unverified, independently of the pair it belongs to --
/// see db.rs's own note on why a verified pair must not imply every
/// differentiator under it is independently reviewed.
#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub fn add_differentiator(
    db: State<Db>,
    pair_id: i64,
    characteristic: String,
    species_a_value: String,
    species_b_value: String,
    reliability_notes: Option<String>,
    source: Option<String>,
    added_by: Option<String>,
) -> Result<i64, String> {
    if characteristic.trim().is_empty()
        || species_a_value.trim().is_empty()
        || species_b_value.trim().is_empty()
    {
        return Err("characteristic and both species' values are required".into());
    }
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO lookalike_differentiators
            (pair_id, characteristic, species_a_value, species_b_value, reliability_notes,
             source, verified, added_by)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0, ?7)",
        params![
            pair_id,
            characteristic.trim(),
            species_a_value.trim(),
            species_b_value.trim(),
            reliability_notes,
            source,
            added_by
        ],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn verify_differentiator(
    db: State<Db>,
    differentiator_id: i64,
    verified_by: Option<String>,
) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let changed = conn
        .execute(
            "UPDATE lookalike_differentiators SET verified = 1, verified_by = ?2, verified_at = datetime('now')
             WHERE id = ?1",
            params![differentiator_id, verified_by],
        )
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err(format!("no differentiator with id {differentiator_id}"));
    }
    Ok(())
}

#[tauri::command]
pub fn delete_differentiator(db: State<Db>, differentiator_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "DELETE FROM lookalike_differentiators WHERE id = ?1",
        params![differentiator_id],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Real fixed step order, picked from the actual coverage numbers checked
/// before building this (data/baneward.db, 2026-11-01): each of these
/// covers 1,950-2,060 of the 2,058 species with any USDA PlantCharacteristics
/// data at all, with a clean, small set of real values -- not every
/// characteristic name in the table is like this (most are yes/no
/// agricultural-use flags, useless for visual identification).
const WIZARD_STEPS: [&str; 5] = [
    "Flower Color",
    "Foliage Color",
    "Shape and Orientation",
    "Bloom Period",
    "Fruit/Seed Color",
];

#[tauri::command]
pub fn wizard_steps() -> Vec<String> {
    WIZARD_STEPS.iter().map(|s| s.to_string()).collect()
}

#[derive(Deserialize)]
pub struct WizardSelection {
    pub characteristic: String,
    pub value: String,
}

#[derive(Serialize)]
pub struct WizardStepOption {
    pub value: String,
    pub count: i64,
}

#[derive(Serialize)]
pub struct WizardCandidate {
    pub symbol: String,
    pub scientific_name: String,
    pub common_name: Option<String>,
    pub family: Option<String>,
    pub has_poisonous_claim: bool,
    /// How many of the user's selections this species actually has a
    /// recorded, matching value for -- vs. just not being excluded because
    /// the trait is undocumented for it. A real design requirement (see
    /// ROADMAP.md v2): missing data is a distinct "unknown" state, never
    /// silently the same as "confirmed." Sorted to the top, but never used
    /// to drop a candidate -- an unindexed dangerous species must never
    /// become invisible just because it can't be found by trait.
    pub confirmed_count: i64,
}

/// Builds the real "keep this species" clause shared by both wizard
/// commands below -- a species stays a candidate if, for every selection,
/// EITHER it has no recorded value for that characteristic at all (real
/// unknown, not a mismatch) OR its recorded value matches what was picked.
/// This is the one rule that makes the whole feature safe to use: a
/// strict filter would silently vanish the ~94% of species with no
/// characteristic data the moment anyone answered a single question.
fn wizard_where_clause(selections: &[WizardSelection]) -> (String, Vec<String>) {
    let mut clauses = Vec::new();
    let mut params: Vec<String> = Vec::new();
    for sel in selections {
        clauses.push(
            "(NOT EXISTS (SELECT 1 FROM characteristics c WHERE c.species_symbol = s.symbol AND c.name = ?)
              OR EXISTS (SELECT 1 FROM characteristics c WHERE c.species_symbol = s.symbol AND c.name = ? AND c.value = ?))"
                .to_string(),
        );
        params.push(sel.characteristic.clone());
        params.push(sel.characteristic.clone());
        params.push(sel.value.clone());
    }
    let where_sql = if clauses.is_empty() {
        "1=1".to_string()
    } else {
        clauses.join(" AND ")
    };
    (where_sql, params)
}

/// Real option counts for the next wizard step, computed against the
/// candidates still standing after the user's selections so far -- not a
/// static, drifting hardcoded list (see v2's own browse-by-feature
/// requirement, same rule applies here).
#[tauri::command]
pub fn wizard_options(
    db: State<Db>,
    characteristic: String,
    selections: Vec<WizardSelection>,
) -> Result<Vec<WizardStepOption>, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let (where_sql, filter_params) = wizard_where_clause(&selections);
    let sql = format!(
        "SELECT c.value, COUNT(DISTINCT s.symbol)
         FROM species s
         JOIN characteristics c ON c.species_symbol = s.symbol AND c.name = ?1
         WHERE {where_sql}
         GROUP BY c.value
         ORDER BY COUNT(DISTINCT s.symbol) DESC"
    );
    let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
    let mut all_params: Vec<&dyn rusqlite::ToSql> = vec![&characteristic];
    for p in &filter_params {
        all_params.push(p);
    }
    let rows = stmt
        .query_map(all_params.as_slice(), |row| {
            Ok(WizardStepOption {
                value: row.get(0)?,
                count: row.get(1)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    Ok(rows)
}

#[tauri::command]
pub fn wizard_search(
    db: State<Db>,
    selections: Vec<WizardSelection>,
) -> Result<Vec<WizardCandidate>, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let (where_sql, filter_params) = wizard_where_clause(&selections);

    let confirmed_sql = if selections.is_empty() {
        "0".to_string()
    } else {
        let per_selection: Vec<String> = selections
            .iter()
            .map(|_| "(cc.name = ? AND cc.value = ?)".to_string())
            .collect();
        // COUNT(DISTINCT cc.name), not COUNT(*) -- data/dedupe_characteristics.py
        // fixed the real duplicate-row bug this was covering for (37,175
        // duplicate rows found live, 2026-11-01), but counting distinct
        // characteristic names is the correct query regardless: this must
        // never exceed selections.len(), whatever state the underlying
        // data is in.
        format!(
            "(SELECT COUNT(DISTINCT cc.name) FROM characteristics cc WHERE cc.species_symbol = s.symbol AND ({}))",
            per_selection.join(" OR ")
        )
    };
    let confirmed_params: Vec<String> = selections
        .iter()
        .flat_map(|sel| vec![sel.characteristic.clone(), sel.value.clone()])
        .collect();

    let sql = format!(
        "SELECT s.symbol, s.scientific_name, s.common_name, s.family,
                EXISTS(SELECT 1 FROM claims c WHERE c.species_symbol = s.symbol
                       AND c.category = 'poisonous' AND c.verified = 1) AS has_poisonous_claim,
                {confirmed_sql} AS confirmed_count
         FROM species s
         WHERE {where_sql}
         ORDER BY confirmed_count DESC, s.common_name, s.scientific_name
         LIMIT 200"
    );

    let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
    let mut all_params: Vec<&dyn rusqlite::ToSql> = Vec::new();
    for p in &confirmed_params {
        all_params.push(p);
    }
    for p in &filter_params {
        all_params.push(p);
    }
    let rows = stmt
        .query_map(all_params.as_slice(), |row| {
            Ok(WizardCandidate {
                symbol: row.get(0)?,
                scientific_name: row.get(1)?,
                common_name: row.get(2)?,
                family: row.get(3)?,
                has_poisonous_claim: row.get(4)?,
                confirmed_count: row.get(5)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    Ok(rows)
}

/// Real facet set for the visual browse view -- the wizard's own 5 plus 3
/// more with the same real coverage/value-count check applied (1,500+
/// species, a clean small set of real values). Deliberately does NOT
/// include `Toxicity`: that field is an NRCS agricultural/conservation
/// judgment, not a verified human-safety claim (see db.rs's own note on
/// `characteristics`), and letting someone filter-browse by it would dress
/// it up as equivalent to the real `claims` system. It stays visible in a
/// species' own Characteristics section, just not promoted into a filter.
const BROWSE_FACETS: [&str; 8] = [
    "Flower Color",
    "Foliage Color",
    "Shape and Orientation",
    "Bloom Period",
    "Fruit/Seed Color",
    "Growth Form",
    "Active Growth Period",
    "Foliage Texture",
];

#[tauri::command]
pub fn browse_facet_names() -> Vec<String> {
    BROWSE_FACETS.iter().map(|s| s.to_string()).collect()
}

#[derive(Serialize)]
pub struct BrowseFacet {
    pub characteristic: String,
    pub options: Vec<WizardStepOption>,
}

/// Real option counts for every facet at once, each computed against the
/// candidates implied by every *other* facet's current selection (not its
/// own) -- so switching a facet's own value still shows real counts for
/// every option in that facet, standard faceted-search behavior, not the
/// wizard's single-next-question model.
#[tauri::command]
pub fn browse_facets(
    db: State<Db>,
    selections: Vec<WizardSelection>,
) -> Result<Vec<BrowseFacet>, String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    for characteristic in BROWSE_FACETS {
        let other: Vec<WizardSelection> = selections
            .iter()
            .filter(|s| s.characteristic != characteristic)
            .map(|s| WizardSelection {
                characteristic: s.characteristic.clone(),
                value: s.value.clone(),
            })
            .collect();
        let (where_sql, filter_params) = wizard_where_clause(&other);
        let sql = format!(
            "SELECT c.value, COUNT(DISTINCT s.symbol)
             FROM species s
             JOIN characteristics c ON c.species_symbol = s.symbol AND c.name = ?1
             WHERE {where_sql}
             GROUP BY c.value
             ORDER BY COUNT(DISTINCT s.symbol) DESC"
        );
        let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
        let mut all_params: Vec<&dyn rusqlite::ToSql> = vec![&characteristic];
        for p in &filter_params {
            all_params.push(p);
        }
        let options = stmt
            .query_map(all_params.as_slice(), |row| {
                Ok(WizardStepOption {
                    value: row.get(0)?,
                    count: row.get(1)?,
                })
            })
            .map_err(|e| e.to_string())?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|e| e.to_string())?;
        out.push(BrowseFacet {
            characteristic: characteristic.to_string(),
            options,
        });
    }
    Ok(out)
}
