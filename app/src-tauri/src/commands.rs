//! Tauri commands — the real search/browse/edit surface over the local
//! database. The one rule every write path here follows (see README.md):
//! `add_claim` always inserts unverified; nothing here can make a claim
//! appear verified except the separate, deliberate `verify_claim` call.

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
    pub url: String,
    pub is_public_domain: bool,
    pub photographer: Option<String>,
    pub institution: Option<String>,
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
