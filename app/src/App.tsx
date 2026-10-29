import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface SpeciesSummary {
  symbol: string;
  scientific_name: string;
  common_name: string | null;
  family: string | null;
  has_poisonous_claim: boolean;
  matched_via: "common_name" | "scientific_name" | "synonym";
  matched_synonym: string | null;
}

interface ImageInfo {
  url: string;
  is_public_domain: boolean;
  photographer: string | null;
  institution: string | null;
}

interface ClaimInfo {
  id: number;
  category: string;
  plant_part: string | null;
  description: string;
  evidence_type: string;
  verified: boolean;
  source: string | null;
  reference: string | null;
  region: string | null;
  added_by: string | null;
  added_at: string;
  verified_by: string | null;
  verified_at: string | null;
}

interface CharacteristicInfo {
  name: string;
  value: string | null;
  category: string | null;
}

interface ActivityInfo {
  activity: string;
  dosage: string | null;
  reference: string | null;
}

interface ChemicalInfo {
  name: string;
  plant_part: string | null;
  activities: ActivityInfo[];
}

interface SpeciesDetail {
  symbol: string;
  scientific_name: string;
  authorship: string | null;
  common_name: string | null;
  family: string | null;
  duration: string | null;
  growth_habit: string | null;
  native_status: string | null;
  source_url: string | null;
  images: ImageInfo[];
  claims: ClaimInfo[];
  chemicals: ChemicalInfo[];
  characteristics: CharacteristicInfo[];
  synonyms: string[];
}

const CATEGORIES = ["poisonous", "edible", "medical", "useful"] as const;
const EVIDENCE_TYPES = [
  "unspecified",
  "traditional",
  "laboratory",
  "animal_study",
  "human_clinical",
  "regulatory",
] as const;

const EVIDENCE_LABELS: Record<string, string> = {
  unspecified: "Unspecified",
  traditional: "Traditional/ethnobotanical use",
  laboratory: "Laboratory finding",
  animal_study: "Animal study",
  human_clinical: "Human clinical evidence",
  regulatory: "Regulatory/government source",
};

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SpeciesSummary[]>([]);
  const [selected, setSelected] = useState<SpeciesDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>("poisonous");
  const [description, setDescription] = useState("");
  const [plantPart, setPlantPart] = useState("");
  const [evidenceType, setEvidenceType] = useState<(typeof EVIDENCE_TYPES)[number]>("unspecified");
  const [source, setSource] = useState("");
  const [reference, setReference] = useState("");
  const [region, setRegion] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const r = await invoke<SpeciesSummary[]>("search_species", { query });
        setResults(r);
      } catch (e) {
        console.error("search failed", e);
      }
    }, 200);
  }, [query]);

  async function openSpecies(symbol: string) {
    setLoadingDetail(true);
    try {
      const detail = await invoke<SpeciesDetail>("get_species", { symbol });
      setSelected(detail);
    } catch (e) {
      console.error("load species failed", e);
    } finally {
      setLoadingDetail(false);
    }
  }

  async function refreshSelected() {
    if (selected) await openSpecies(selected.symbol);
  }

  async function submitClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !description.trim()) return;
    try {
      await invoke("add_claim", {
        symbol: selected.symbol,
        category,
        description: description.trim(),
        plantPart: plantPart.trim() || null,
        evidenceType,
        source: source.trim() || null,
        reference: reference.trim() || null,
        region: region.trim() || null,
        addedBy: "local-user",
      });
      setDescription("");
      setPlantPart("");
      setSource("");
      setReference("");
      setRegion("");
      await refreshSelected();
    } catch (e) {
      console.error("add_claim failed", e);
    }
  }

  async function verify(claimId: number) {
    await invoke("verify_claim", { claimId, verifiedBy: "local-user" });
    await refreshSelected();
  }

  async function removeClaim(claimId: number) {
    await invoke("delete_claim", { claimId });
    await refreshSelected();
  }

  const usableImages = selected?.images.filter((i) => i.is_public_domain) ?? [];
  const claimsByCategory = (selected?.claims ?? []).reduce<Record<string, ClaimInfo[]>>((acc, c) => {
    (acc[c.category] ??= []).push(c);
    return acc;
  }, {});

  return (
    <main className="shell">
      <header className="header">
        <h1>🌿 Baneward</h1>
        <p className="tagline">Offline US wild plant reference — 35,326 species, zero assumed safety claims</p>
      </header>

      <div className="layout">
        <div className="search-pane">
          <input
            autoFocus
            className="search-box"
            placeholder="Search by common or scientific name…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul className="results">
            {results.map((r) => (
              <li
                key={r.symbol}
                className={`result ${selected?.symbol === r.symbol ? "active" : ""}`}
                onClick={() => openSpecies(r.symbol)}
              >
                <span className="common">{r.common_name ?? r.scientific_name}</span>
                <span className="sci">
                  <i>{r.scientific_name}</i>
                  {r.family ? ` · ${r.family}` : ""}
                </span>
                {r.matched_via === "synonym" && r.matched_synonym && (
                  <span className="matched-via">
                    matched via old name <i>{r.matched_synonym}</i>
                  </span>
                )}
                {r.has_poisonous_claim && <span className="pill pill-danger">⚠ POISONOUS</span>}
              </li>
            ))}
            {query.trim().length >= 2 && results.length === 0 && (
              <li className="empty">No matches.</li>
            )}
          </ul>
        </div>

        <div className="detail-pane">
          {loadingDetail && <p>Loading…</p>}
          {!loadingDetail && !selected && (
            <p className="placeholder">Search for a plant to see what's known about it.</p>
          )}
          {!loadingDetail && selected && (
            <div className="detail">
              <h2>
                {selected.common_name ?? selected.scientific_name}
              </h2>
              <p className="sci-name">
                <i>{selected.scientific_name}</i> {selected.authorship}
                {selected.family ? ` · ${selected.family}` : ""}
              </p>
              {selected.synonyms.length > 0 && (
                <p className="synonyms">
                  Also known as:{" "}
                  {selected.synonyms.map((s, i) => (
                    <span key={s}>
                      {i > 0 && ", "}
                      <i>{s}</i>
                    </span>
                  ))}
                </p>
              )}

              <dl className="facts">
                {selected.duration && (
                  <>
                    <dt>Duration</dt>
                    <dd>{selected.duration}</dd>
                  </>
                )}
                {selected.growth_habit && (
                  <>
                    <dt>Growth habit</dt>
                    <dd>{selected.growth_habit}</dd>
                  </>
                )}
                {selected.native_status && (
                  <>
                    <dt>Native status</dt>
                    <dd>{selected.native_status}</dd>
                  </>
                )}
              </dl>

              {selected.characteristics.length > 0 ? (
                <section className="characteristics-section">
                  <h3>Characteristics</h3>
                  <p className="form-note">
                    Real USDA PLANTS data — documented for only about 1 in 17 species, so
                    this section is empty for most. Agricultural/conservation-use
                    judgments (e.g. "Toxicity"), not a verified human-safety claim —
                    treat alongside Claims below, not instead of it.
                  </p>
                  {Object.entries(
                    selected.characteristics.reduce<Record<string, CharacteristicInfo[]>>((acc, c) => {
                      const cat = c.category ?? "Other";
                      (acc[cat] ??= []).push(c);
                      return acc;
                    }, {})
                  ).map(([cat, items]) => (
                    <div key={cat} className="char-group">
                      <h4>{cat}</h4>
                      <dl className="facts">
                        {items.map((c) => (
                          <>
                            <dt key={c.name + "-dt"}>{c.name}</dt>
                            <dd key={c.name + "-dd"}>{c.value ?? "—"}</dd>
                          </>
                        ))}
                      </dl>
                    </div>
                  ))}
                </section>
              ) : (
                <p className="no-images">No USDA characteristics documented for this species.</p>
              )}

              {selected.chemicals.length > 0 && (
                <section className="chemistry-section">
                  <h3>Chemistry</h3>
                  <p className="form-note">
                    Real documented chemicals (Dr. Duke's Phytochemical and Ethnobotanical
                    Databases, USDA ARS) — present for only about 1 in 26 species. Raw
                    laboratory/literature findings about the chemical itself, not a safety
                    or therapeutic claim about this plant — see Claims below for that.
                  </p>
                  {selected.chemicals.map((c) => (
                    <details key={c.name} className="chem-group">
                      <summary>
                        {c.name}
                        {c.plant_part && <span className="chem-part"> ({c.plant_part})</span>}
                        {c.activities.length > 0 && (
                          <span className="chem-count"> — {c.activities.length} documented bioactivit{c.activities.length !== 1 ? "ies" : "y"}</span>
                        )}
                      </summary>
                      {c.activities.length > 0 ? (
                        <ul className="activity-list">
                          {c.activities.map((a, i) => (
                            <li key={i}>
                              <span className="activity-name">{a.activity}</span>
                              {a.dosage && <span className="activity-dosage"> {a.dosage}</span>}
                              {a.reference && <span className="activity-ref"> — {a.reference}</span>}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="no-claims">No specific bioactivity documented beyond presence.</p>
                      )}
                    </details>
                  ))}
                </section>
              )}

              {usableImages.length > 0 ? (
                <div className="images">
                  {usableImages.slice(0, 6).map((img) => (
                    <figure key={img.url}>
                      <img src={img.url} alt={selected.common_name ?? selected.scientific_name} loading="lazy" />
                      <figcaption>{img.photographer ?? img.institution ?? "USDA PLANTS"}</figcaption>
                    </figure>
                  ))}
                </div>
              ) : (
                <p className="no-images">
                  No public-domain image on file for this species
                  {selected.images.length > 0 ? " (all existing photos are copyrighted)." : "."}
                </p>
              )}

              <section className="claims-section">
                <h3>Claims</h3>
                {selected.claims.length === 0 && (
                  <p className="no-claims">
                    Not yet classified. No claim — medical, poisonous, edible, or useful — has
                    been entered for this species.
                  </p>
                )}

                {CATEGORIES.filter((cat) => claimsByCategory[cat]?.length).map((cat) => {
                  const items = claimsByCategory[cat];
                  const verifiedCount = items.filter((c) => c.verified).length;
                  return (
                    <details key={cat} className={`claim-group claim-group-${cat}`} open={items.length <= 5}>
                      <summary>
                        {cat.toUpperCase()} — {items.length} claim{items.length !== 1 ? "s" : ""}
                        {verifiedCount > 0 && <span className="verified-count"> ({verifiedCount} verified)</span>}
                      </summary>
                      <ul className="claim-list">
                        {items.map((c) => (
                          <li key={c.id} className={`claim ${c.verified ? "verified" : "unverified"}`}>
                            <div className="claim-head">
                              <span className="claim-evidence">{EVIDENCE_LABELS[c.evidence_type] ?? c.evidence_type}</span>
                              <span className={`claim-status ${c.verified ? "status-verified" : "status-unverified"}`}>
                                {c.verified ? "✓ Verified" : "⚠ Unverified"}
                              </span>
                            </div>
                            <p className="claim-description">{c.description}</p>
                            <p className="claim-meta">
                              {c.plant_part && <span>Part: {c.plant_part}</span>}
                              {c.region && <span>Region: {c.region}</span>}
                            </p>
                            {(c.source || c.reference) && (
                              <p className="claim-source">
                                {c.source}
                                {c.source && c.reference && " — "}
                                {c.reference}
                              </p>
                            )}
                            <div className="claim-actions">
                              {!c.verified && <button onClick={() => verify(c.id)}>Mark verified</button>}
                              <button className="danger" onClick={() => removeClaim(c.id)}>
                                Remove
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </details>
                  );
                })}

                <form className="add-claim-form" onSubmit={submitClaim}>
                  <h4>Add a claim</h4>
                  <p className="form-note">
                    New claims start unverified. They won't show as confirmed until someone
                    explicitly marks them verified against a real source.
                  </p>
                  <div className="form-row">
                    <select value={category} onChange={(e) => setCategory(e.target.value as typeof category)}>
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    <select value={evidenceType} onChange={(e) => setEvidenceType(e.target.value as typeof evidenceType)}>
                      {EVIDENCE_TYPES.map((e) => (
                        <option key={e} value={e}>
                          {EVIDENCE_LABELS[e]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <textarea
                    placeholder="What's the claim, and why?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                  <div className="form-row">
                    <input
                      placeholder="Plant part (optional — root, leaf, berry…)"
                      value={plantPart}
                      onChange={(e) => setPlantPart(e.target.value)}
                    />
                    <input
                      placeholder="Region (optional)"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                    />
                  </div>
                  <input
                    placeholder="Source (optional, but a real one helps verification later)"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                  />
                  <input
                    placeholder="Reference / citation (optional)"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                  />
                  <button type="submit" disabled={!description.trim()}>
                    Add unverified claim
                  </button>
                </form>
              </section>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
