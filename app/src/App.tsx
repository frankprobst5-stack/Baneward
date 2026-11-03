import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
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

interface ImagePackStatus {
  source: string;
  total: number;
  downloaded: number;
  pack_size_mb: number;
}

const SOURCE_LABELS: Record<string, string> = {
  inaturalist: "iNaturalist (community photos)",
  wikidata_commons: "Wikimedia Commons / Wikidata",
  smithsonian: "Smithsonian National Museum of Natural History",
};

interface ImageInfo {
  id: number;
  url: string;
  is_public_domain: boolean;
  photographer: string | null;
  institution: string | null;
  source: string;
  verified: boolean;
  added_by: string | null;
  added_at: string | null;
  data_base64: string | null;
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

interface DistributionEntry {
  level: "state" | "county";
  subdivision_name: string;
  nativity_status: string | null;
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

interface LookalikeSummary {
  pair_id: number;
  other_symbol: string;
  other_common_name: string | null;
  other_scientific_name: string;
  risk_level: "fatal" | "severe" | "moderate" | "mild";
  summary: string;
  verified: boolean;
}

interface LookalikeSpeciesInfo {
  symbol: string;
  scientific_name: string;
  common_name: string | null;
  family: string | null;
}

interface DifferentiatorInfo {
  id: number;
  characteristic: string;
  species_a_value: string;
  species_b_value: string;
  reliability_notes: string | null;
  source: string | null;
  verified: boolean;
  added_by: string | null;
  added_at: string;
  verified_by: string | null;
  verified_at: string | null;
}

interface LookalikePairDetail {
  id: number;
  species_a: LookalikeSpeciesInfo;
  species_b: LookalikeSpeciesInfo;
  risk_level: "fatal" | "severe" | "moderate" | "mild";
  summary: string;
  verified: boolean;
  added_by: string | null;
  added_at: string;
  verified_by: string | null;
  verified_at: string | null;
  differentiators: DifferentiatorInfo[];
}

interface WizardStepOption {
  value: string;
  count: number;
}

interface WizardCandidate {
  symbol: string;
  scientific_name: string;
  common_name: string | null;
  family: string | null;
  has_poisonous_claim: boolean;
  confirmed_count: number;
}

interface WizardSelectionEntry {
  characteristic: string;
  value: string;
}

interface BrowseFacet {
  characteristic: string;
  options: WizardStepOption[];
}

interface FieldNoteInfo {
  id: number;
  species_symbol: string | null;
  species_common_name: string | null;
  species_scientific_name: string | null;
  observation: string;
  location: string | null;
  observed_at: string | null;
  added_by: string | null;
  added_at: string;
}

const WIZARD_STEP_QUESTIONS: Record<string, string> = {
  "Flower Color": "What color are the flowers?",
  "Foliage Color": "What color is the foliage?",
  "Shape and Orientation": "What's the plant's growth form?",
  "Bloom Period": "When does (or did) it bloom?",
  "Fruit/Seed Color": "What color is the fruit or seed?",
};

const RISK_LABELS: Record<string, string> = {
  fatal: "⚠ Fatal risk",
  severe: "⚠ Severe risk",
  moderate: "Moderate risk",
  mild: "Mild risk",
};

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
  lookalikes: LookalikeSummary[];
  field_notes: FieldNoteInfo[];
  distribution: DistributionEntry[];
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
  const [userImageData, setUserImageData] = useState<Record<number, string>>({});
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [packStatus, setPackStatus] = useState<ImagePackStatus[]>([]);
  const [downloadingPack, setDownloadingPack] = useState<string | null>(null);
  const [packError, setPackError] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<LookalikePairDetail | null>(null);
  const [loadingPair, setLoadingPair] = useState(false);
  const [diffCharacteristic, setDiffCharacteristic] = useState("");
  const [diffValueA, setDiffValueA] = useState("");
  const [diffValueB, setDiffValueB] = useState("");
  const [diffNotes, setDiffNotes] = useState("");
  const [diffSource, setDiffSource] = useState("");
  const [wizardMode, setWizardMode] = useState(false);
  const [wizardSteps, setWizardSteps] = useState<string[]>([]);
  const [wizardStepIndex, setWizardStepIndex] = useState(0);
  const [wizardSelections, setWizardSelections] = useState<WizardSelectionEntry[]>([]);
  const [wizardOptions, setWizardOptions] = useState<WizardStepOption[]>([]);
  const [wizardResults, setWizardResults] = useState<WizardCandidate[] | null>(null);
  const [loadingWizard, setLoadingWizard] = useState(false);
  const [browseMode, setBrowseMode] = useState(false);
  const [browseFacets, setBrowseFacets] = useState<BrowseFacet[]>([]);
  const [browseSelections, setBrowseSelections] = useState<WizardSelectionEntry[]>([]);
  const [browseResults, setBrowseResults] = useState<WizardCandidate[]>([]);
  const [loadingBrowse, setLoadingBrowse] = useState(false);
  const [fieldNotesMode, setFieldNotesMode] = useState(false);
  const [allFieldNotes, setAllFieldNotes] = useState<FieldNoteInfo[]>([]);
  const [loadingFieldNotes, setLoadingFieldNotes] = useState(false);
  const [noteObservation, setNoteObservation] = useState("");
  const [noteLocation, setNoteLocation] = useState("");
  const [noteObservedAt, setNoteObservedAt] = useState("");
  const [aiMode, setAiMode] = useState(false);
  const [aiDescription, setAiDescription] = useState("");
  const [aiParsing, setAiParsing] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    invoke<ImagePackStatus[]>("image_pack_status")
      .then(setPackStatus)
      .catch((e) => console.error("image_pack_status failed", e));
  }, []);

  async function downloadPack(src: string) {
    setDownloadingPack(src);
    setPackError(null);
    try {
      await invoke("download_image_pack", { source: src });
      const status = await invoke<ImagePackStatus[]>("image_pack_status");
      setPackStatus(status);
      await refreshSelected();
    } catch (e) {
      setPackError(String(e));
    } finally {
      setDownloadingPack(null);
    }
  }

  async function openPair(pairId: number) {
    setLoadingPair(true);
    try {
      const detail = await invoke<LookalikePairDetail>("get_lookalike_pair", { pairId });
      setSelectedPair(detail);
    } catch (e) {
      console.error("get_lookalike_pair failed", e);
    } finally {
      setLoadingPair(false);
    }
  }

  function closePair() {
    setSelectedPair(null);
    setDiffCharacteristic("");
    setDiffValueA("");
    setDiffValueB("");
    setDiffNotes("");
    setDiffSource("");
  }

  async function refreshPair() {
    if (selectedPair) await openPair(selectedPair.id);
  }

  async function verifyPair(pairId: number) {
    await invoke("verify_lookalike_pair", { pairId, verifiedBy: "local-user" });
    await refreshPair();
    await refreshSelected();
  }

  async function submitDifferentiator(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPair || !diffCharacteristic.trim() || !diffValueA.trim() || !diffValueB.trim()) return;
    try {
      await invoke("add_differentiator", {
        pairId: selectedPair.id,
        characteristic: diffCharacteristic.trim(),
        speciesAValue: diffValueA.trim(),
        speciesBValue: diffValueB.trim(),
        reliabilityNotes: diffNotes.trim() || null,
        source: diffSource.trim() || null,
        addedBy: "local-user",
      });
      setDiffCharacteristic("");
      setDiffValueA("");
      setDiffValueB("");
      setDiffNotes("");
      setDiffSource("");
      await refreshPair();
    } catch (e) {
      console.error("add_differentiator failed", e);
    }
  }

  async function verifyDiff(diffId: number) {
    await invoke("verify_differentiator", { differentiatorId: diffId, verifiedBy: "local-user" });
    await refreshPair();
  }

  async function removeDiff(diffId: number) {
    await invoke("delete_differentiator", { differentiatorId: diffId });
    await refreshPair();
  }

  async function loadWizardOptions(characteristic: string, selections: WizardSelectionEntry[]) {
    setLoadingWizard(true);
    try {
      const opts = await invoke<WizardStepOption[]>("wizard_options", { characteristic, selections });
      setWizardOptions(opts);
    } catch (e) {
      console.error("wizard_options failed", e);
    } finally {
      setLoadingWizard(false);
    }
  }

  async function startWizard() {
    closePair();
    setSelected(null);
    setBrowseMode(false);
    setFieldNotesMode(false);
    setAiMode(false);
    setWizardMode(true);
    setWizardStepIndex(0);
    setWizardSelections([]);
    setWizardResults(null);
    try {
      const steps = await invoke<string[]>("wizard_steps");
      setWizardSteps(steps);
      if (steps.length > 0) await loadWizardOptions(steps[0], []);
    } catch (e) {
      console.error("wizard_steps failed", e);
    }
  }

  function exitWizard() {
    setWizardMode(false);
    setWizardResults(null);
  }

  async function showWizardResults(selections: WizardSelectionEntry[]) {
    setLoadingWizard(true);
    try {
      const results = await invoke<WizardCandidate[]>("wizard_search", { selections });
      setWizardResults(results);
    } catch (e) {
      console.error("wizard_search failed", e);
    } finally {
      setLoadingWizard(false);
    }
  }

  async function chooseWizardOption(value: string | null) {
    const characteristic = wizardSteps[wizardStepIndex];
    const newSelections = value ? [...wizardSelections, { characteristic, value }] : wizardSelections;
    setWizardSelections(newSelections);
    const nextIndex = wizardStepIndex + 1;
    if (nextIndex >= wizardSteps.length) {
      await showWizardResults(newSelections);
    } else {
      setWizardStepIndex(nextIndex);
      await loadWizardOptions(wizardSteps[nextIndex], newSelections);
    }
  }

  function wizardGoBack() {
    if (wizardResults) {
      setWizardResults(null);
      return;
    }
    if (wizardStepIndex === 0) return;
    const prevIndex = wizardStepIndex - 1;
    const trimmed = wizardSelections.slice(0, prevIndex);
    setWizardSelections(trimmed);
    setWizardStepIndex(prevIndex);
    loadWizardOptions(wizardSteps[prevIndex], trimmed);
  }

  async function pickWizardCandidate(symbol: string) {
    exitWizard();
    await openSpecies(symbol);
  }

  async function refreshBrowse(selections: WizardSelectionEntry[]) {
    setLoadingBrowse(true);
    try {
      const [facets, results] = await Promise.all([
        invoke<BrowseFacet[]>("browse_facets", { selections }),
        selections.length > 0 ? invoke<WizardCandidate[]>("wizard_search", { selections }) : Promise.resolve([]),
      ]);
      setBrowseFacets(facets);
      setBrowseResults(results);
    } catch (e) {
      console.error("browse refresh failed", e);
    } finally {
      setLoadingBrowse(false);
    }
  }

  async function startBrowse() {
    closePair();
    setSelected(null);
    setWizardMode(false);
    setFieldNotesMode(false);
    setAiMode(false);
    setBrowseMode(true);
    setBrowseSelections([]);
    setBrowseResults([]);
    await refreshBrowse([]);
  }

  function exitBrowse() {
    setBrowseMode(false);
  }

  function toggleBrowseFilter(characteristic: string, value: string) {
    const existing = browseSelections.find((s) => s.characteristic === characteristic);
    let next: WizardSelectionEntry[];
    if (existing && existing.value === value) {
      next = browseSelections.filter((s) => s.characteristic !== characteristic);
    } else if (existing) {
      next = browseSelections.map((s) => (s.characteristic === characteristic ? { characteristic, value } : s));
    } else {
      next = [...browseSelections, { characteristic, value }];
    }
    setBrowseSelections(next);
    refreshBrowse(next);
  }

  async function pickBrowseCandidate(symbol: string) {
    exitBrowse();
    await openSpecies(symbol);
  }

  async function refreshFieldNotesLog() {
    setLoadingFieldNotes(true);
    try {
      const notes = await invoke<FieldNoteInfo[]>("list_field_notes");
      setAllFieldNotes(notes);
    } catch (e) {
      console.error("list_field_notes failed", e);
    } finally {
      setLoadingFieldNotes(false);
    }
  }

  async function startFieldNotesLog() {
    closePair();
    setSelected(null);
    setWizardMode(false);
    setBrowseMode(false);
    setAiMode(false);
    setFieldNotesMode(true);
    await refreshFieldNotesLog();
  }

  function exitFieldNotesLog() {
    setFieldNotesMode(false);
  }

  async function submitFieldNote(e: React.FormEvent, speciesSymbol: string | null) {
    e.preventDefault();
    if (!noteObservation.trim()) return;
    try {
      await invoke("add_field_note", {
        speciesSymbol,
        observation: noteObservation.trim(),
        location: noteLocation.trim() || null,
        observedAt: noteObservedAt || null,
        addedBy: "local-user",
      });
      setNoteObservation("");
      setNoteLocation("");
      setNoteObservedAt("");
      if (speciesSymbol) await refreshSelected();
      if (fieldNotesMode) await refreshFieldNotesLog();
    } catch (e) {
      console.error("add_field_note failed", e);
    }
  }

  async function removeFieldNote(noteId: number, speciesSymbol: string | null) {
    await invoke("delete_field_note", { noteId });
    if (speciesSymbol) await refreshSelected();
    if (fieldNotesMode) await refreshFieldNotesLog();
  }

  async function openNoteSpecies(symbol: string) {
    exitFieldNotesLog();
    await openSpecies(symbol);
  }

  function startAiDescribe() {
    closePair();
    setSelected(null);
    setWizardMode(false);
    setBrowseMode(false);
    setFieldNotesMode(false);
    setAiMode(true);
    setAiDescription("");
    setAiError(null);
  }

  function exitAiDescribe() {
    setAiMode(false);
  }

  async function submitAiDescribe(e: React.FormEvent) {
    e.preventDefault();
    if (!aiDescription.trim()) return;
    setAiParsing(true);
    setAiError(null);
    try {
      const selections = await invoke<WizardSelectionEntry[]>("ai_parse_description", {
        description: aiDescription.trim(),
      });
      setAiMode(false);
      setBrowseMode(true);
      setBrowseSelections(selections);
      await refreshBrowse(selections);
    } catch (e) {
      setAiError(String(e));
    } finally {
      setAiParsing(false);
    }
  }

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

  // User-uploaded photos live as local files, not http(s) URLs -- read_image_bytes
  // turns each one into a data URI an <img> can actually use. USDA images already
  // have a plain URL and skip this entirely.
  useEffect(() => {
    const userImages = selected?.images.filter((i) => i.source === "user_upload") ?? [];
    userImages.forEach((img) => {
      if (userImageData[img.id]) return;
      invoke<string>("read_image_bytes", { path: img.url })
        .then((dataUri) => setUserImageData((prev) => ({ ...prev, [img.id]: dataUri })))
        .catch((e) => console.error("read_image_bytes failed", e));
    });
  }, [selected]);

  async function uploadPhoto() {
    if (!selected) return;
    setUploadError(null);
    const path = await open({
      multiple: false,
      filters: [{ name: "Image", extensions: ["jpg", "jpeg", "png", "webp", "gif"] }],
    });
    if (!path) return; // cancelled
    setUploadingPhoto(true);
    try {
      await invoke("add_user_image", { symbol: selected.symbol, path, addedBy: "local-user" });
      await refreshSelected();
    } catch (e) {
      setUploadError(String(e));
    } finally {
      setUploadingPhoto(false);
    }
  }

  async function verifyImage(imageId: number) {
    await invoke("verify_user_image", { imageId, verifiedBy: "local-user" });
    await refreshSelected();
  }

  async function removeImage(imageId: number) {
    await invoke("delete_user_image", { imageId });
    setUserImageData((prev) => {
      const next = { ...prev };
      delete next[imageId];
      return next;
    });
    await refreshSelected();
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

  const COMMUNITY_SOURCES = ["inaturalist", "wikidata_commons", "smithsonian"] as const;
  const usableImages = selected?.images.filter((i) => i.source === "usda_plants" && i.is_public_domain) ?? [];
  const userPhotos = selected?.images.filter((i) => i.source === "user_upload") ?? [];
  const communityPhotos = selected?.images.filter((i) => (COMMUNITY_SOURCES as readonly string[]).includes(i.source)) ?? [];
  const communityPhotosBySource = communityPhotos.reduce<Record<string, ImageInfo[]>>((acc, img) => {
    (acc[img.source] ??= []).push(img);
    return acc;
  }, {});
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
          <button type="button" className="wizard-entry" onClick={startWizard}>
            🌿 Don't know the name? Identify by what it looks like
          </button>
          <button type="button" className="wizard-entry" onClick={startBrowse}>
            🔍 Browse the catalog by trait
          </button>
          <button type="button" className="wizard-entry" onClick={startFieldNotesLog}>
            📝 My field notes
          </button>
          <button type="button" className="wizard-entry" onClick={startAiDescribe}>
            🤖 Describe what you saw (local AI)
          </button>
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
          {wizardMode && (
            <div className="wizard">
              <button type="button" className="back-link" onClick={exitWizard}>
                ✕ Exit identification wizard
              </button>
              {wizardResults === null ? (
                <>
                  <h2>{WIZARD_STEP_QUESTIONS[wizardSteps[wizardStepIndex]] ?? wizardSteps[wizardStepIndex]}</h2>
                  <p className="form-note">
                    Step {wizardStepIndex + 1} of {wizardSteps.length}. A species with no recorded
                    data for this trait stays a candidate — missing data is never treated the same
                    as "doesn't have this."
                  </p>
                  {loadingWizard ? (
                    <p>Loading…</p>
                  ) : (
                    <div className="wizard-options">
                      {wizardOptions.map((opt) => (
                        <button type="button" key={opt.value} className="wizard-option" onClick={() => chooseWizardOption(opt.value)}>
                          {opt.value} <span className="wizard-option-count">({opt.count})</span>
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="wizard-nav">
                    {wizardStepIndex > 0 && (
                      <button type="button" onClick={wizardGoBack}>
                        ← Back
                      </button>
                    )}
                    <button type="button" onClick={() => chooseWizardOption(null)}>
                      I don't know / skip this
                    </button>
                    <button type="button" onClick={() => showWizardResults(wizardSelections)}>
                      See candidates so far ({wizardSelections.length} trait{wizardSelections.length !== 1 ? "s" : ""} selected)
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <h2>Candidates ({wizardResults.length})</h2>
                  <p className="form-note">
                    Sorted by how many of your {wizardSelections.length} selected trait
                    {wizardSelections.length !== 1 ? "s" : ""} each one actually has confirmed —
                    not a guarantee, just a starting point. A plant with "0 confirmed" wasn't
                    excluded only because it has no recorded data for those traits.
                  </p>
                  <button type="button" onClick={wizardGoBack}>
                    ← Back to questions
                  </button>
                  <ul className="results wizard-results">
                    {wizardResults.map((c) => (
                      <li key={c.symbol} className="result" onClick={() => pickWizardCandidate(c.symbol)}>
                        <span className="common">{c.common_name ?? c.scientific_name}</span>
                        <span className="sci">
                          <i>{c.scientific_name}</i>
                          {c.family ? ` · ${c.family}` : ""}
                        </span>
                        <span className="matched-via">
                          {c.confirmed_count} of {wizardSelections.length} confirmed
                        </span>
                        {c.has_poisonous_claim && <span className="pill pill-danger">⚠ POISONOUS</span>}
                      </li>
                    ))}
                    {wizardResults.length === 0 && <li className="empty">No candidates found.</li>}
                  </ul>
                </>
              )}
            </div>
          )}
          {browseMode && (
            <div className="browse">
              <button type="button" className="back-link" onClick={exitBrowse}>
                ✕ Exit browse
              </button>
              <h2>Browse by trait</h2>
              <p className="form-note">
                Pick any combination of traits in any order. A species with no recorded
                data for a trait is never excluded by it — only a documented, different
                value excludes it.
              </p>
              <div className="browse-facets">
                {browseFacets.map((facet) => {
                  const selected = browseSelections.find((s) => s.characteristic === facet.characteristic);
                  return (
                    <div className="browse-facet" key={facet.characteristic}>
                      <h4>{facet.characteristic}</h4>
                      <div className="wizard-options">
                        {facet.options.map((opt) => (
                          <button
                            type="button"
                            key={opt.value}
                            className={`wizard-option ${selected?.value === opt.value ? "active" : ""}`}
                            onClick={() => toggleBrowseFilter(facet.characteristic, opt.value)}
                          >
                            {opt.value} <span className="wizard-option-count">({opt.count})</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              {loadingBrowse && <p>Loading…</p>}
              {!loadingBrowse && browseSelections.length === 0 && (
                <p className="placeholder">Select at least one trait above to see candidates.</p>
              )}
              {!loadingBrowse && browseSelections.length > 0 && (
                <>
                  <h3>Candidates ({browseResults.length})</h3>
                  <p className="form-note">
                    Sorted by how many of your {browseSelections.length} selected trait
                    {browseSelections.length !== 1 ? "s" : ""} each one actually has confirmed —
                    "0 confirmed" means unindexed for those traits, not ruled out.
                  </p>
                  <ul className="results wizard-results">
                    {browseResults.map((c) => (
                      <li key={c.symbol} className="result" onClick={() => pickBrowseCandidate(c.symbol)}>
                        <span className="common">{c.common_name ?? c.scientific_name}</span>
                        <span className="sci">
                          <i>{c.scientific_name}</i>
                          {c.family ? ` · ${c.family}` : ""}
                        </span>
                        <span className="matched-via">
                          {c.confirmed_count} of {browseSelections.length} confirmed
                        </span>
                        {c.has_poisonous_claim && <span className="pill pill-danger">⚠ POISONOUS</span>}
                      </li>
                    ))}
                    {browseResults.length === 0 && <li className="empty">No candidates found.</li>}
                  </ul>
                </>
              )}
            </div>
          )}
          {fieldNotesMode && (
            <div className="field-notes-log">
              <button type="button" className="back-link" onClick={exitFieldNotesLog}>
                ✕ Exit field notes
              </button>
              <h2>My Field Notes</h2>
              <p className="form-note">
                Your own observations, not reviewed identifications — a note can exist
                before you know what the plant is. Add one here without linking it to a
                species, or add one from a species' own detail page to link it there.
              </p>
              <form className="add-claim-form" onSubmit={(e) => submitFieldNote(e, null)}>
                <h4>Add a field note</h4>
                <textarea
                  placeholder="What did you see? Where, what did it look like…"
                  value={noteObservation}
                  onChange={(e) => setNoteObservation(e.target.value)}
                />
                <div className="form-row">
                  <input
                    placeholder="Location (optional)"
                    value={noteLocation}
                    onChange={(e) => setNoteLocation(e.target.value)}
                  />
                  <input
                    type="date"
                    value={noteObservedAt}
                    onChange={(e) => setNoteObservedAt(e.target.value)}
                  />
                </div>
                <button type="submit" disabled={!noteObservation.trim()}>
                  Add field note
                </button>
              </form>

              {loadingFieldNotes && <p>Loading…</p>}
              {!loadingFieldNotes && allFieldNotes.length === 0 && (
                <p className="placeholder">No field notes yet.</p>
              )}
              {!loadingFieldNotes && allFieldNotes.length > 0 && (
                <ul className="claim-list">
                  {allFieldNotes.map((note) => (
                    <li key={note.id} className="claim">
                      <div className="claim-head">
                        <span className="claim-evidence">
                          {note.species_symbol ? (
                            <button type="button" className="lookalike-link" onClick={() => openNoteSpecies(note.species_symbol!)}>
                              {note.species_common_name ?? note.species_scientific_name}
                            </button>
                          ) : (
                            "Unidentified"
                          )}
                        </span>
                        {note.observed_at && <span className="claim-status">{note.observed_at}</span>}
                      </div>
                      <p className="claim-description">{note.observation}</p>
                      {note.location && <p className="claim-source">📍 {note.location}</p>}
                      <div className="claim-actions">
                        <button type="button" className="danger" onClick={() => removeFieldNote(note.id, note.species_symbol)}>
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {aiMode && (
            <div className="ai-describe">
              <button type="button" className="back-link" onClick={exitAiDescribe}>
                ✕ Exit AI describe
              </button>
              <h2>Describe what you saw</h2>
              <p className="form-note">
                A local AI (your own machine's Ollama, not a cloud service) turns your
                description into trait filters — it only recognizes flower/foliage/fruit
                color, growth form, and bloom period, the same traits the wizard and browse
                views use, and anything it suggests still goes through real validation
                against the database before being used. It never identifies a species or
                makes a safety determination by itself — it just sets up the same search
                you could build manually, and you review the result before using it.
              </p>
              <form onSubmit={submitAiDescribe} className="add-claim-form">
                <textarea
                  placeholder="e.g. Tall plant with white umbrella-shaped flowers blooming in early summer, purple blotches on the stem…"
                  value={aiDescription}
                  onChange={(e) => setAiDescription(e.target.value)}
                />
                <button type="submit" disabled={!aiDescription.trim() || aiParsing}>
                  {aiParsing ? "Thinking…" : "Find matching traits"}
                </button>
              </form>
              {aiError && (
                <p className="error-text">
                  {aiError} — the rest of Baneward works fine without this; try the
                  wizard or browse view instead.
                </p>
              )}
            </div>
          )}
          {!wizardMode && !browseMode && !fieldNotesMode && !aiMode && (
            <>
          {loadingPair && <p>Loading comparison…</p>}
          {!loadingPair && selectedPair && (
            <div className="comparison">
              <button type="button" className="back-link" onClick={closePair}>
                ← Back to species
              </button>
              <h2>
                {RISK_LABELS[selectedPair.risk_level]}: {selectedPair.species_a.common_name ?? selectedPair.species_a.scientific_name}
                {" vs. "}
                {selectedPair.species_b.common_name ?? selectedPair.species_b.scientific_name}
              </h2>
              <p className="comparison-summary">{selectedPair.summary}</p>
              <p className="comparison-caveat">
                No single feature below is a safe identification method on its own — check
                multiple characteristics, and when in doubt, don't eat it.
              </p>
              <div className="comparison-status">
                <span className={`claim-status ${selectedPair.verified ? "status-verified" : "status-unverified"}`}>
                  {selectedPair.verified ? "Pair reviewed" : "Pair not yet reviewed"}
                </span>
                {!selectedPair.verified && (
                  <button type="button" onClick={() => verifyPair(selectedPair.id)}>
                    Mark pair reviewed
                  </button>
                )}
              </div>

              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Characteristic</th>
                    <th>
                      <i>{selectedPair.species_a.scientific_name}</i>
                      {selectedPair.species_a.common_name ? ` (${selectedPair.species_a.common_name})` : ""}
                    </th>
                    <th>
                      <i>{selectedPair.species_b.scientific_name}</i>
                      {selectedPair.species_b.common_name ? ` (${selectedPair.species_b.common_name})` : ""}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {selectedPair.differentiators.map((d) => (
                    <tr key={d.id} className={d.verified ? "verified" : "unverified"}>
                      <td>
                        {d.characteristic}
                        <div className={`claim-status ${d.verified ? "status-verified" : "status-unverified"}`}>
                          {d.verified ? "Verified" : "Unverified"}
                        </div>
                      </td>
                      <td>{d.species_a_value}</td>
                      <td>{d.species_b_value}</td>
                      <td className="diff-meta">
                        {d.reliability_notes && <div className="reliability-notes">{d.reliability_notes}</div>}
                        {d.source && <div className="diff-source">{d.source}</div>}
                        <div className="user-photo-actions">
                          {!d.verified && (
                            <button type="button" onClick={() => verifyDiff(d.id)}>
                              Verify
                            </button>
                          )}
                          <button type="button" className="danger" onClick={() => removeDiff(d.id)}>
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {selectedPair.differentiators.length === 0 && (
                    <tr>
                      <td colSpan={4} className="no-claims">
                        No differentiators entered yet for this pair.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

              <form className="add-claim-form" onSubmit={submitDifferentiator}>
                <h4>Add a differentiator</h4>
                <p className="form-note">
                  New differentiators start unverified, independently of the pair itself.
                </p>
                <input
                  placeholder="Characteristic (e.g. stem markings)"
                  value={diffCharacteristic}
                  onChange={(e) => setDiffCharacteristic(e.target.value)}
                />
                <div className="form-row">
                  <input
                    placeholder={`${selectedPair.species_a.common_name ?? selectedPair.species_a.scientific_name}'s value`}
                    value={diffValueA}
                    onChange={(e) => setDiffValueA(e.target.value)}
                  />
                  <input
                    placeholder={`${selectedPair.species_b.common_name ?? selectedPair.species_b.scientific_name}'s value`}
                    value={diffValueB}
                    onChange={(e) => setDiffValueB(e.target.value)}
                  />
                </div>
                <input
                  placeholder="Reliability notes (optional — e.g. 'present in all growth stages')"
                  value={diffNotes}
                  onChange={(e) => setDiffNotes(e.target.value)}
                />
                <input
                  placeholder="Source (optional, but a real one helps verification later)"
                  value={diffSource}
                  onChange={(e) => setDiffSource(e.target.value)}
                />
                <button type="submit" disabled={!diffCharacteristic.trim() || !diffValueA.trim() || !diffValueB.trim()}>
                  Add unverified differentiator
                </button>
              </form>
            </div>
          )}
          {!loadingPair && !selectedPair && (
            <>
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

              {selected.lookalikes.length > 0 && (
                <div className="lookalike-warning">
                  <strong>⚠ Often confused with:</strong>
                  <ul>
                    {selected.lookalikes.map((l) => (
                      <li key={l.pair_id}>
                        <button type="button" className="lookalike-link" onClick={() => openPair(l.pair_id)}>
                          {l.other_common_name ?? l.other_scientific_name}
                        </button>{" "}
                        <span className={`risk-badge risk-${l.risk_level}`}>{RISK_LABELS[l.risk_level]}</span>
                        {!l.verified && <span className="claim-status status-unverified"> (unreviewed)</span>}
                        <p className="lookalike-summary">{l.summary}</p>
                      </li>
                    ))}
                  </ul>
                </div>
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

              {selected.distribution.length > 0 ? (
                <section className="distribution-section">
                  <h3>Where it grows</h3>
                  <p className="form-note">
                    Real USDA/NRCS state and county occurrence data — coverage isn't
                    universal, a real check found roughly a quarter to a third of species
                    have no record here at all. "Introduced" means documented outside its
                    native range, not a safety judgment.
                  </p>
                  {selected.distribution
                    .filter((d) => d.level === "state")
                    .map((s) => (
                      <span
                        key={s.subdivision_name}
                        className={`dist-chip dist-${s.nativity_status ?? "unknown"}`}
                      >
                        {s.subdivision_name}
                        {s.nativity_status && ` (${s.nativity_status})`}
                      </span>
                    ))}
                  {selected.distribution.some((d) => d.level === "county") && (
                    <details className="distribution-counties">
                      <summary>
                        {selected.distribution.filter((d) => d.level === "county").length}{" "}
                        counties/parishes documented
                      </summary>
                      <div className="distribution-county-list">
                        {selected.distribution
                          .filter((d) => d.level === "county")
                          .map((c) => (
                            <span
                              key={c.subdivision_name}
                              className={`dist-chip dist-${c.nativity_status ?? "unknown"}`}
                            >
                              {c.subdivision_name}
                            </span>
                          ))}
                      </div>
                    </details>
                  )}
                </section>
              ) : (
                <p className="no-images">
                  No state/county distribution data documented for this species in this
                  source.
                </p>
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

              {Object.entries(communityPhotosBySource).map(([src, imgs]) => {
                const downloaded = imgs.filter((i) => i.data_base64);
                const notDownloaded = imgs.filter((i) => !i.data_base64);
                const status = packStatus.find((p) => p.source === src);
                return (
                  <section className="community-photos-section" key={src}>
                    <h3>Community Photos ({SOURCE_LABELS[src] ?? src})</h3>
                    <p className="form-note">
                      {src === "inaturalist"
                        ? "Research-grade on iNaturalist — at least two independent people agreed on the identification — which is real, but it's a community ID, not USDA's own institutional data."
                        : src === "smithsonian"
                        ? "A real Smithsonian specimen record, tied to this species by GBIF's own exact taxonomic match."
                        : "Linked via Wikidata's own taxon-to-image record, cross-checked against the genus before being accepted."}{" "}
                      Cached locally (CC0/CC-BY only) so it works offline; starts unverified like
                      everything that isn't USDA's own.
                    </p>
                    {notDownloaded.length > 0 && (
                      <div className="pack-prompt">
                        <p>
                          {notDownloaded.length} more photo{notDownloaded.length !== 1 ? "s" : ""} available
                          from {SOURCE_LABELS[src] ?? src}, not yet downloaded to this install
                          {status ? ` (full pack ~${status.pack_size_mb >= 1000 ? (status.pack_size_mb / 1000).toFixed(1) + " GB" : Math.round(status.pack_size_mb) + " MB"})` : ""}.
                        </p>
                        <button type="button" onClick={() => downloadPack(src)} disabled={downloadingPack === src}>
                          {downloadingPack === src ? "Downloading…" : `Download ${SOURCE_LABELS[src] ?? src} photo pack`}
                        </button>
                        {packError && downloadingPack === null && <p className="error-text">{packError}</p>}
                      </div>
                    )}
                    {downloaded.length > 0 && (
                  <div className="images">
                    {downloaded.map((img) => (
                      <figure key={img.id} className={img.verified ? "verified" : "unverified"}>
                        <img src={img.data_base64!} alt={selected.common_name ?? selected.scientific_name} loading="lazy" />
                        <figcaption>
                          <span className={`claim-status ${img.verified ? "status-verified" : "status-unverified"}`}>
                            {img.verified ? "Verified" : "Unverified"}
                          </span>
                          <div className="attribution-text">{img.photographer}</div>
                          <div className="user-photo-actions">
                            {!img.verified && (
                              <button type="button" onClick={() => verifyImage(img.id)}>
                                Verify
                              </button>
                            )}
                            <button type="button" className="danger" onClick={() => removeImage(img.id)}>
                              Remove
                            </button>
                          </div>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                    )}
                  </section>
                );
              })}

              <section className="user-photos-section">
                <h3>Your Photos</h3>
                <p className="form-note">
                  A photo you add here is a claim that this is what the species looks
                  like, same as a text claim — it starts unverified, and nothing here
                  makes it a confirmed identification by itself.
                </p>
                {userPhotos.length > 0 && (
                  <div className="images">
                    {userPhotos.map((img) => (
                      <figure key={img.id} className={img.verified ? "verified" : "unverified"}>
                        {userImageData[img.id] ? (
                          <img src={userImageData[img.id]} alt="user-submitted" loading="lazy" />
                        ) : (
                          <div className="image-loading">Loading…</div>
                        )}
                        <figcaption>
                          <span className={`claim-status ${img.verified ? "status-verified" : "status-unverified"}`}>
                            {img.verified ? "Verified" : "Unverified"}
                          </span>
                          <div className="user-photo-actions">
                            {!img.verified && (
                              <button type="button" onClick={() => verifyImage(img.id)}>
                                Verify
                              </button>
                            )}
                            <button type="button" className="danger" onClick={() => removeImage(img.id)}>
                              Remove
                            </button>
                          </div>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                )}
                <button type="button" onClick={uploadPhoto} disabled={uploadingPhoto}>
                  {uploadingPhoto ? "Adding…" : "+ Add your own photo"}
                </button>
                {uploadError && <p className="error-text">{uploadError}</p>}
              </section>

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

              <section className="field-notes-section">
                <h3>Field Notes</h3>
                <p className="form-note">
                  Your own observations of this species — not a reviewed claim, just a
                  personal record of what you saw.
                </p>
                {selected.field_notes.length === 0 && (
                  <p className="no-claims">No field notes for this species yet.</p>
                )}
                {selected.field_notes.length > 0 && (
                  <ul className="claim-list">
                    {selected.field_notes.map((note) => (
                      <li key={note.id} className="claim">
                        {note.observed_at && (
                          <div className="claim-head">
                            <span className="claim-status">{note.observed_at}</span>
                          </div>
                        )}
                        <p className="claim-description">{note.observation}</p>
                        {note.location && <p className="claim-source">📍 {note.location}</p>}
                        <div className="claim-actions">
                          <button type="button" className="danger" onClick={() => removeFieldNote(note.id, selected.symbol)}>
                            Remove
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                <form className="add-claim-form" onSubmit={(e) => submitFieldNote(e, selected.symbol)}>
                  <h4>Add a field note</h4>
                  <textarea
                    placeholder="What did you see? Where, what did it look like…"
                    value={noteObservation}
                    onChange={(e) => setNoteObservation(e.target.value)}
                  />
                  <div className="form-row">
                    <input
                      placeholder="Location (optional)"
                      value={noteLocation}
                      onChange={(e) => setNoteLocation(e.target.value)}
                    />
                    <input
                      type="date"
                      value={noteObservedAt}
                      onChange={(e) => setNoteObservedAt(e.target.value)}
                    />
                  </div>
                  <button type="submit" disabled={!noteObservation.trim()}>
                    Add field note
                  </button>
                </form>
              </section>
            </div>
          )}
            </>
          )}
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
