//! Tauri commands — the real search/browse/edit surface over the local
//! database. The one rule every write path here follows (see README.md):
//! `add_tag` always inserts unverified; nothing here can make a tag
//! appear verified except the separate, deliberate `verify_tag` call.

use crate::db::Db;
use rusqlite::params;
use serde::Serialize;
use tauri::State;

#[derive(Serialize)]
pub struct SpeciesSummary {
    pub symbol: String,
    pub scientific_name: String,
    pub common_name: Option<String>,
    pub family: Option<String>,
    pub has_poisonous_tag: bool,
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
                    EXISTS(SELECT 1 FROM tags t WHERE t.species_symbol = s.symbol
                           AND t.tag_type = 'poisonous' AND t.verified = 1) AS has_poisonous_tag,
                    CASE WHEN s.common_name LIKE ?1 THEN 'common_name' ELSE 'scientific_name' END AS matched_via,
                    NULL AS matched_synonym,
                    0 AS rank
             FROM species s
             WHERE s.scientific_name LIKE ?1 OR s.common_name LIKE ?1

             UNION ALL

             SELECT s.symbol, s.scientific_name, s.common_name, s.family,
                    EXISTS(SELECT 1 FROM tags t WHERE t.species_symbol = s.symbol
                           AND t.tag_type = 'poisonous' AND t.verified = 1) AS has_poisonous_tag,
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
                has_poisonous_tag: row.get(4)?,
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
    pub url: String,
    pub is_public_domain: bool,
    pub photographer: Option<String>,
    pub institution: Option<String>,
}

#[derive(Serialize)]
pub struct TagInfo {
    pub id: i64,
    pub tag_type: String,
    pub value: String,
    pub verified: bool,
    pub source: Option<String>,
    pub added_by: Option<String>,
    pub added_at: String,
}

#[derive(Serialize)]
pub struct CharacteristicInfo {
    pub name: String,
    pub value: Option<String>,
    pub category: Option<String>,
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
    pub tags: Vec<TagInfo>,
    /// Real USDA PlantCharacteristics data — present for only ~5.8% of
    /// species (confirmed, not assumed universal). An empty list means
    /// genuinely undocumented, not "nothing interesting."
    pub characteristics: Vec<CharacteristicInfo>,
    /// Older/alternate scientific names that resolve to this species.
    pub synonyms: Vec<String>,
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
                    tags: Vec::new(),
                    characteristics: Vec::new(),
                    synonyms: Vec::new(),
                })
            },
        )
        .map_err(|e| format!("species not found: {e}"))?;

    let mut img_stmt = conn
        .prepare(
            "SELECT url, is_public_domain, photographer, institution
             FROM images WHERE species_symbol = ?1 ORDER BY is_public_domain DESC",
        )
        .map_err(|e| e.to_string())?;
    species.images = img_stmt
        .query_map(params![species.symbol], |row| {
            Ok(ImageInfo {
                url: row.get(0)?,
                is_public_domain: row.get(1)?,
                photographer: row.get(2)?,
                institution: row.get(3)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    let mut tag_stmt = conn
        .prepare(
            "SELECT id, tag_type, value, verified, source, added_by, added_at
             FROM tags WHERE species_symbol = ?1 ORDER BY verified DESC, added_at DESC",
        )
        .map_err(|e| e.to_string())?;
    species.tags = tag_stmt
        .query_map(params![species.symbol], |row| {
            Ok(TagInfo {
                id: row.get(0)?,
                tag_type: row.get(1)?,
                value: row.get(2)?,
                verified: row.get(3)?,
                source: row.get(4)?,
                added_by: row.get(5)?,
                added_at: row.get(6)?,
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

    Ok(species)
}

const VALID_TAG_TYPES: [&str; 4] = ["medical", "poisonous", "edible", "useful"];

/// Always inserts unverified (verified = 0). This is the one rule in the
/// whole app that must never bend: adding a tag is never, by itself,
/// enough to make a claim visible as confirmed.
#[tauri::command]
pub fn add_tag(
    db: State<Db>,
    symbol: String,
    tag_type: String,
    value: String,
    source: Option<String>,
    added_by: Option<String>,
) -> Result<i64, String> {
    if !VALID_TAG_TYPES.contains(&tag_type.as_str()) {
        return Err(format!(
            "invalid tag_type '{tag_type}', must be one of {VALID_TAG_TYPES:?}"
        ));
    }
    if value.trim().is_empty() {
        return Err("tag value can't be empty".into());
    }

    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO tags (species_symbol, tag_type, value, verified, source, added_by)
         VALUES (?1, ?2, ?3, 0, ?4, ?5)",
        params![symbol, tag_type, value.trim(), source, added_by],
    )
    .map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

/// The only path by which a tag becomes verified — a separate, explicit
/// call, never a side effect of add_tag or an edit.
#[tauri::command]
pub fn verify_tag(db: State<Db>, tag_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    let changed = conn
        .execute("UPDATE tags SET verified = 1 WHERE id = ?1", params![tag_id])
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err(format!("no tag with id {tag_id}"));
    }
    Ok(())
}

#[tauri::command]
pub fn delete_tag(db: State<Db>, tag_id: i64) -> Result<(), String> {
    let conn = db.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM tags WHERE id = ?1", params![tag_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
