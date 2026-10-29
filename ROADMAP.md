# Baneward — Roadmap

Real, dated, honest about what's done vs. planned — same discipline every other project in
the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem) uses.

## Where things stand (2026-10-27)

Repo created, name chosen (`Baneward` — "bane" = poison, as in wolfsbane/henbane, + "ward" =
guard/protect, naming the core red-alert-for-poison feature directly). **Phase 0 is fully
done**: all 35,326 real US species are enriched and sitting in a real local database, zero
failures, verified against live sources throughout — not assumed. Two of the three
originally-planned sources turned out not to hold up on direct verification; the plan was
corrected in response, not papered over. See below for the full detail.

## Phase 0 — Prove the data pipeline ✅ done 2026-10-27

**Real correction, found by actually testing each source rather than trusting the original
research summary:**
- **USDA ARS's "International Checklist of Poisonous Plants" doesn't exist as a free,
  bulk-downloadable government dataset.** What's actually live today is a commercially
  published, copyrighted book (*International Poisonous Plants Checklist: An Evidence-Based
  Reference*, CRC Press, 2010). The 1998 USDA paper that described free web access to a
  checklist database doesn't correspond to anything on GRIN's current site
  (confirmed by fetching `ars-grin.gov` directly — no mention of it anywhere).
- **Wikidata's structured "poisonous plant" class was tried as a replacement — also too
  thin.** A real SPARQL query against `wikidata.org/wiki/Q21028485` returns exactly **30
  plants total**. Nowhere near comprehensive enough.
- **BRIT's Native American Ethnobotany Database (naeb.brit.org) was unreachable** during
  this pass (connection refused on both http and https) — status unconfirmed, not
  necessarily dead, just not yet re-verified.

**Revised plan, Frank's own call**: don't block on a perfect toxicity/edibility source up
front. Build the real database from USDA PLANTS (confirmed solid) first, with `medical` /
`poisonous` / `edible` / `useful` as an editable tag layer that starts **empty per species,
not defaulted to any claim** — missing tags mean "not yet classified," never "safe." Add
real sourcing (Wikipedia's own cited toxicity sections were identified as the most promising
real replacement for the poison data specifically — CC-BY-SA, bulk-accessible via its API,
not yet pipeline-tested) once the base database is real and populated.

**USDA PLANTS pipeline — verified real, end to end, 2026-10-27**:
- Bulk taxonomy: `https://hosted-datasets.gbif.org/datasets/usda.zip` — real, current
  (synced 2 days before this was tested), **CC0 licensed** (confirmed directly from the
  package's own `metadata.yaml`, not inferred). 93,983 names (~49,000 accepted taxa + ~44,000
  synonyms), as `NameUsage.tsv` + `VernacularName.tsv`.
- Enrichment API confirmed live: `plantsservices.sc.egov.usda.gov/api/PlantProfile?symbol=X`
  returns real distribution, growth habit, duration, and a plant ID.
- Images confirmed live and correctly licensed per-image:
  `api/PlantImages?plantId=X` returns each image's real `Copyright: true/false` flag plus
  photographer/institution attribution — exactly as the original research predicted, this
  time actually tested. Real image URLs
  (`plants.sc.egov.usda.gov/ImageLibrary/standard/<file>.jpg`) confirmed to return real
  JPEGs.
- The API's `Ethnobotanies` field, which looked like it might shortcut the edible/medicinal
  side, was tested against several well-known food/medicine plants (purple coneflower,
  cattail, common milkweed) and came back empty every time — a real dead end, not a usable
  source, ruled out by testing rather than assumed to work from the schema alone.

**Real working prototype built**: `data/build_phase0.py` ingests 10 deliberately chosen real
species — well-known deadly plants (water hemlock, poison hemlock), well-known edibles/
medicinals (cattail, milkweed, coneflower, nettle, pokeweed), skin-contact toxins (poison
ivy, poison oak), and the classic dangerous look-alike pair (poison hemlock vs. wild
carrot/Queen Anne's lace) — into a real local SQLite database (`species`/`images`/`tags`
tables). Confirmed: real scientific/common names, family, duration, growth habit all
populated correctly; images correctly split by real copyright status (poison oak's own 8
images, for instance, are honestly all copyrighted — 0 usable, not glossed over); tags table
empty except one deliberate demonstration entry (water hemlock, marked verified, cited to
CDC NIOSH and USDA ARS) proving the edit/verification mechanism itself works.

**Scaled to the real full dataset, 2026-10-27, same day**: `data/ingest_full.py` — a
resumable, cached, 10-worker version of the same proven pipeline — ran against all
**35,326 accepted, species-rank taxa** (deliberately excluding varieties/subspecies/
synonyms; a forager needs "water hemlock," not six named varieties of it). **56 minutes,
zero failures, every single species enriched.** Real final numbers:

- **35,326 species**, full taxonomy/distribution/growth-habit/duration/common names.
- **44,243 images** fetched, of which **18,121 are confirmed public-domain and usable**
  (the rest correctly excluded as copyrighted, not discarded from the record — just not
  surfaced as usable).
- **7,676 species already have at least one real usable photo.**
- Database: `data/baneward.db`, 16MB — small enough to live comfortably offline on
  anything.
- Spot-checked: searching "hemlock" or "ivy" correctly surfaces all three real water
  hemlocks (*Cicuta maculata*, *C. douglasii*, *C. bulbifera*) alongside unrelated
  same-word species (hemlock dwarf mistletoe, ivyleaf maple) without confusing them —
  real disambiguation, not just a keyword match.

Tags table: still empty for all 35,326 species except the one original demonstration
entry (water hemlock, marked verified, cited) — exactly by design. Phase 0's job was the
pipeline, not the editorial pass; nothing here claims a plant is safe.

**Real open questions, not resolved yet**:
- Re-verify BRIT's NAEB site (may have been a transient connectivity issue, not confirmed
  dead).
- Pipeline-test Wikipedia's own toxicity content as the real poison-data source, the same
  way USDA PLANTS just got tested — not yet done, this was ruled promising but unverified.
- How a "red-alert" severity gets derived honestly once a real poison-data source is
  pipeline-tested, rather than invented.
- Images themselves aren't downloaded/cached locally yet, only their URLs and copyright
  status — a real offline-first build needs the actual image bytes, not links to a service
  that won't be reachable grid-down. That's real Phase 1 work, not done here.

## Phase 1 — Real standalone app, matching WayStation's own stack ✅ working scaffold 2026-10-28

Frank's own clarification on why "build it like WayStation" matters: so people can run it
as a fully standalone app on its own, *or* plug it into Citadel the same optional way
WayStation does — not an either/or. That settles the stack question Phase 0 left open:
**Tauri v2 + React 19 + TypeScript + Rust, same as WayStation**, not a lighter-weight
alternative.

**Real app built and verified, `app/`**:
- Rust backend (`src-tauri/`): `rusqlite` (bundled SQLite, no system dependency),
  `tauri-plugin-single-instance` + `tauri-plugin-deep-link` registered in the same order
  and with the same real reasoning as WayStation's own `lib.rs` (single-instance first, so
  a second launch focuses the existing window instead of fighting over the same database
  file) — `baneward://` is the scheme, mirroring `waystation://` exactly, registered now
  even though the Citadel-side launch tile is real Phase 3 work, not done here.
- The real 35,326-species database ships **bundled inside the app itself**
  (`src-tauri/resources/baneward.db`, 16MB) and gets copied into the user's own real
  per-OS app data directory on first run only — verified live: a fresh launch against an
  empty `BANEWARD_DATA_DIR` correctly bootstrapped all 35,326 species from the bundled
  copy, and a second launch correctly left the user's own (by-then-possibly-edited) copy
  alone rather than overwriting it with a newer bundled resource. This is the real
  mechanism that makes "runs standalone, data already inside" true, not just a claim.
- Three real commands: `search_species` (common/scientific name, poisonous species
  surfaced with a flag), `get_species` (full detail + images + tags), `add_tag` /
  `verify_tag` / `delete_tag`. The safety rule is enforced in the Rust layer, not just the
  UI: `add_tag`'s own SQL hardcodes `verified = 0` — there's no parameter a careless
  frontend change could flip to bypass it. `verify_tag` is the only path to a confirmed
  tag, and it's a separate, deliberate call.
- Real UI: search-and-select on the left, species detail (taxonomy, duration, growth
  habit, native status) on the right, public-domain images only (copyrighted ones
  correctly excluded, not shown), tags listed with a visible verified/unverified badge, and
  an add-tag form whose own copy says plainly that new tags start unverified. Same Citadel
  Ecosystem dark palette (literal hex values) as WayStation's own.
- **Real bug found during verification, not left in**: the full-scale ingest
  (`data/ingest_full.py`) rebuilds the whole database from scratch every run, which
  silently dropped the one demonstration tag `data/build_phase0.py` had proven the
  mechanism with — caught by testing the app's actual search query against the real
  bundled database, not assumed correct. Fixed with a small, separate,
  idempotent `data/seed_demo_tag.py` — deliberately not folded into `ingest_full.py`
  itself, so a real demonstration entry never gets mistaken for ingested USDA data.
- Verified for real: `cargo check` clean, `npm run build` (tsc + vite) clean, a real debug
  build compiled and ran (`cargo tauri dev`, ~2.5 minutes cold / ~1 minute incremental, both
  on this real machine's own display), stayed alive, no panics. Visual confirmation of the
  rendered window itself wasn't possible in this session (no screenshot tool available) —
  worth a real look by actually running `npm run tauri dev` and checking it by eye before
  calling the UI itself done, not just the plumbing.

**Not done yet**: a real app icon (still Tauri's default), the actual `baneward://`
Citadel-side launch tile (Phase 3), and everything Phase 1's original scope named that
isn't search/tag-editing — image bytes cached locally instead of live USDA URLs (today's
UI still needs the internet to show a photo), and any real UX pass beyond this first
working version.

## Phase 1.5 — Real identification data: synonyms and characteristics ✅ done 2026-10-29

Real feedback from an outside review of Baneward (Frank shared it, asked to review the
ideas): the single biggest weakness is that Baneward could only be searched by a name the
user already knows — no way to find a plant from what they can actually observe. The
review's own proposed fix (structured leaf/flower/habitat characteristics) assumed that
data would need sourcing from scratch. Checked instead: USDA PLANTS already has almost
exactly that, via a second real API endpoint — `PlantCharacteristics` — not used in Phase 0
and undocumented in the data package's own metadata. Found it by intercepting the real
network call USDA's own site makes (it's a path parameter,
`/api/PlantCharacteristics/{plantId}`, not a query string — every earlier guess at the
endpoint shape 404'd until this was confirmed live).

**Real data added, both ingested with a dedicated, resumable script
(`data/ingest_characteristics_and_synonyms.py`)**:
- **30,531 scientific-name synonyms** (of 44,163 total synonym rows in USDA's own data;
  the rest point to genus/family-level or non-species-rank nodes, deliberately not chased
  further) — an older/alternate Latin name now resolves to the current accepted species.
  Real example found verifying this: "seep monkeyflower" alone carries 69 historical
  synonyms from decades of *Mimulus* taxonomic revision.
- **200,872 real characteristic rows across 2,058 species** (confirmed 5.8% coverage, not
  assumed universal — water hemlock itself has none). Real fields: flower/foliage/fruit
  color, growth form, height, bloom period, drought/shade tolerance, and — directly
  relevant to the whole point of this project — `Toxicity` and `Palatable Human`. This is
  NRCS's own agricultural/conservation-use judgment, not a verified human-poisoning
  determination — treated as a real cross-reference signal alongside the Tags system, never
  a substitute for it.

**Wired into the real app, same session**: `search_species` now matches synonyms too and
tells the UI which name actually matched (`matched_via`: common name / scientific name /
synonym) so a result never looks wrong when it was reached through an old name.
`get_species` returns real characteristics (grouped by category, with an honest note about
the ~1-in-17 coverage rate) and the list of known synonyms. Verified against the actual
running app's live database, not just the schema — including a surgical, careful update to
the already-running dev instance's real data file (checked first that no new user tags had
been added since launch, so nothing could be silently lost).

**Correction to the outside review's own sourcing proposal, also checked for real**: it
separately suggested the FDA's decommissioned Poisonous Plant Database as a public-domain
poison-data source. Confirmed directly on FDA's own page: genuinely public domain. But the
actual data endpoint is a real 404 — decommissioned in 2008, now fully offline, not just
de-linked. Same "legitimately public domain but not currently accessible" pattern already
hit once with the ARS Poisonous Plants Checklist in Phase 0. A Wayback Machine snapshot
might still recover it — a real next step, not done here.

## Phase 1.6 — Richer claims schema + real Dr. Duke ethnobotanical data ✅ done 2026-10-29

A second installment of the same outside review proposed a real architectural fix: don't
conflate "what domain is a claim about" with "how do we know it" — a chemical's reported
toxicity in a lab assay isn't the same kind of evidence as a documented human poisoning
case, even if both are about the same `poisonous` category. It also flagged a second real
data source worth checking: Dr. Duke's Phytochemical and Ethnobotanical Database.

**Verified before building anything** (same discipline as every other source this project
has touched): fetched the real USDA ARS listing on data.gov directly — **CC0**, confirmed
from the page itself, no ambiguity. Downloaded the real archive
(`Duke-Source-CSV.zip`, 16 real linked CSV tables, 40MB) and tested match rate before
committing to an ingest: **62.2% of its 82,873 `ETHNOBOT` rows (51,579 real records) match
a species already in our database** — spot-checked against species we know (*Asclepias
syriaca*/common milkweed: real documented Pamunkey traditional use for Cancer, plus
Asthma, Bronchitis, Cathartic, Cough, each with a real bibliographic reference).

**Real schema redesign, `tags` → `claims`** (`app/src-tauri/src/db.rs`,
`data/migrate_claims_schema.py`): kept the existing `category` axis (medical / poisonous /
edible / useful — Baneward's own red-alert logic still keys off this, unchanged) and added
the real missing axis, `evidence_type` (traditional / laboratory / animal_study /
human_clinical / regulatory / unspecified), plus `plant_part`, `reference`, and `region`
fields Duke's real data actually has. The one existing demo claim (water hemlock) migrated
over intact, still verified, nothing lost.

**Real ingest, deliberately scoped to `ETHNOBOT` only**
(`data/ingest_duke_ethnobotany.py`) — the one Duke table that's directly species-level
(genus/species columns) without needing to resolve through Duke's own internal plant-ID
numbering first. The chemical-level tables (`ACTIVITIES`, `AGGREGAC`, `CHEMICALS`,
`CHEM_MEANS`, `FARMACY_NEW`, `DOSAGE`) need that resolution step through `FNFTAX.csv` and
are real, scoped future work, not done here. Every inserted claim: `category='medical'`,
`evidence_type='traditional'` (explicitly not clinical evidence), region and reference
preserved from Duke's own `COUNTRY`/`REFERENCE` columns, **unverified**, same as every
other claim regardless of source — CC0 government data doesn't exempt it from the same
human review before it counts as confirmed.

**Real final numbers**: 51,579 new claims inserted (51,580 total with the original demo
claim), all unverified. Rust backend (`commands.rs`: `add_claim`/`verify_claim`/
`delete_claim`, richer `ClaimInfo`) and the UI (grouped-by-category, collapsible per
category since one species — castor bean — has 202 real claims on its own) both updated
and verified against the real running app's live database, not just the schema — checked
first that no new claims had been added since the last session before migrating the live
copy, same care as Phase 1.5's update.

## Phase 2 — Local AI search integration

Wire up search/explain against Citadel's existing Off-Grid AI (Ollama) infrastructure,
scoped strictly to already-verified entries per `README.md`'s own safety rule — not started,
blocked on Phase 1's storage shape being real first.

## Phase 3 — Tie into Citadel

Once Baneward is real and standalone (matching WayStation's own path to a `waystation://`
launch tile), wire a launch point into Citadel's cockpit. Exact mechanism (a URI scheme like
WayStation's, or something else) not decided — depends on what Phase 1 picks.

## Keeping this current

Same rule as the rest of the ecosystem: this file is the detailed, current source for
Baneward's own work. `citadel-ecosystem/MASTER_ROADMAP.md` gets updated to match when this
one moves, not the other way around.
