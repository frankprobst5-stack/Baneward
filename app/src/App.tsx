import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface SpeciesSummary {
  symbol: string;
  scientific_name: string;
  common_name: string | null;
  family: string | null;
  has_poisonous_tag: boolean;
  matched_via: "common_name" | "scientific_name" | "synonym";
  matched_synonym: string | null;
}

interface ImageInfo {
  url: string;
  is_public_domain: boolean;
  photographer: string | null;
  institution: string | null;
}

interface TagInfo {
  id: number;
  tag_type: string;
  value: string;
  verified: boolean;
  source: string | null;
  added_by: string | null;
  added_at: string;
}

interface CharacteristicInfo {
  name: string;
  value: string | null;
  category: string | null;
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
  tags: TagInfo[];
  characteristics: CharacteristicInfo[];
  synonyms: string[];
}

const TAG_TYPES = ["poisonous", "edible", "medical", "useful"] as const;

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SpeciesSummary[]>([]);
  const [selected, setSelected] = useState<SpeciesDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [tagType, setTagType] = useState<(typeof TAG_TYPES)[number]>("poisonous");
  const [tagValue, setTagValue] = useState("");
  const [tagSource, setTagSource] = useState("");
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

  async function submitTag(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !tagValue.trim()) return;
    try {
      await invoke("add_tag", {
        symbol: selected.symbol,
        tagType,
        value: tagValue.trim(),
        source: tagSource.trim() || null,
        addedBy: "local-user",
      });
      setTagValue("");
      setTagSource("");
      await refreshSelected();
    } catch (e) {
      console.error("add_tag failed", e);
    }
  }

  async function verify(tagId: number) {
    await invoke("verify_tag", { tagId });
    await refreshSelected();
  }

  async function removeTag(tagId: number) {
    await invoke("delete_tag", { tagId });
    await refreshSelected();
  }

  const usableImages = selected?.images.filter((i) => i.is_public_domain) ?? [];

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
                {r.has_poisonous_tag && <span className="pill pill-danger">⚠ POISONOUS</span>}
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
                    treat alongside the Tags section below, not instead of it.
                  </p>
                  {Object.entries(
                    selected.characteristics.reduce<Record<string, CharacteristicInfo[]>>((acc, c) => {
                      const cat = c.category ?? "Other";
                      (acc[cat] ??= []).push(c);
                      return acc;
                    }, {})
                  ).map(([category, items]) => (
                    <div key={category} className="char-group">
                      <h4>{category}</h4>
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

              <section className="tags-section">
                <h3>Tags</h3>
                {selected.tags.length === 0 && (
                  <p className="no-tags">
                    Not yet classified. No claim — medical, poisonous, edible, or useful — has
                    been entered for this species.
                  </p>
                )}
                <ul className="tag-list">
                  {selected.tags.map((t) => (
                    <li key={t.id} className={`tag tag-${t.tag_type} ${t.verified ? "verified" : "unverified"}`}>
                      <div className="tag-head">
                        <span className="tag-type">{t.tag_type.toUpperCase()}</span>
                        <span className={`tag-status ${t.verified ? "status-verified" : "status-unverified"}`}>
                          {t.verified ? "✓ Verified" : "⚠ Unverified"}
                        </span>
                      </div>
                      <p className="tag-value">{t.value}</p>
                      {t.source && <p className="tag-source">Source: {t.source}</p>}
                      <div className="tag-actions">
                        {!t.verified && (
                          <button onClick={() => verify(t.id)}>Mark verified</button>
                        )}
                        <button className="danger" onClick={() => removeTag(t.id)}>
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>

                <form className="add-tag-form" onSubmit={submitTag}>
                  <h4>Add a tag</h4>
                  <p className="form-note">
                    New tags start unverified. They won't show as confirmed until someone
                    explicitly marks them verified against a real source.
                  </p>
                  <select value={tagType} onChange={(e) => setTagType(e.target.value as typeof tagType)}>
                    {TAG_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <textarea
                    placeholder="What's the claim, and why?"
                    value={tagValue}
                    onChange={(e) => setTagValue(e.target.value)}
                  />
                  <input
                    placeholder="Source (optional, but a real one helps verification later)"
                    value={tagSource}
                    onChange={(e) => setTagSource(e.target.value)}
                  />
                  <button type="submit" disabled={!tagValue.trim()}>
                    Add unverified tag
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
