# Baneward — Roadmap

Real, dated, honest about what's done vs. planned — same discipline every other project in
the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem) uses.

## Where things stand (2026-10-29)

Repo created, name chosen (`Baneward` — "bane" = poison, as in wolfsbane/henbane, + "ward" =
guard/protect, naming the core red-alert-for-poison feature directly). **Phase 0 is fully
done**: all 35,326 real US species are enriched and sitting in a real local database, zero
failures, verified against live sources throughout — not assumed. Two of the three
originally-planned sources turned out not to hold up on direct verification; the plan was
corrected in response, not papered over. Phases 1 through 1.9 are also done: a real
standalone Tauri app (matching WayStation's stack), synonym/characteristic search data,
51,580 real ethnobotanical claims, 3,001 real documented chemicals with their lab
bioactivities, a real "add your own photo" feature, and a prototyped iNaturalist image
pipeline (64 real cached community photos, full-scale decision pending) — all unverified
by default, same rule throughout. See below for the full detail.

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

**Real sizing check on that image-caching gap, 2026-10-29**: an outside review estimated
"~150KB/image, ~2.7GB total" for all 18,121 usable images — checked that number directly
rather than repeating it. A real 5-image sample from `plants.sc.egov.usda.gov` came back
13KB–49KB, averaging ~34KB — roughly **~600MB total**, not 2.7GB (small sample, worth a
real full measurement before building around either number, but the order-of-magnitude
correction stands). Still too much to bundle inside a 16MB installer, so a post-install
background download manager is still the right shape — just not the one the estimate made
it look like. Real nuance worth keeping for whenever this gets built: don't make "download
all 18,121" the only offline-capable option — a curated core set (dangerous species, common
edible look-alikes, the photos that best show a distinguishing feature) that ships or syncs
first, with "my region" and "everything" as explicit, sized-up-front opt-ins, serves someone
on a slow or metered connection far better than one all-or-nothing download. And once any
of this exists, it needs a real offline test — launch with networking disabled and confirm
search, cached images, and verified claims all still work, and that nothing silently falls
back to a live USDA URL without saying so.

**Real gap this surfaced that wasn't tracked anywhere yet**: every database update so far
this session (Phase 1.5, 1.6, 1.7) has been applied to the live running app by hand — check
for new user claims first, then `ATTACH DATABASE` the new tables in surgically. That's the
right instinct, but it's not a real mechanism an actual end user could use — they don't have
a terminal and a copy of this repo. Future released updates (corrected taxonomy, new
images, new characteristics) need a real in-app path that can add/update reference data
without ever touching a user's own claims, verifications, or field notes. Not designed yet;
worth deciding before this ships to anyone who isn't also its developer.

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
hit once with the ARS Poisonous Plants Checklist in Phase 0. **Follow-up done, closed as
unrecoverable for now**: checked the Wayback Machine for a snapshot of the old endpoint —
partial evidence only (some crawled HTML, no intact dataset) before the Internet Archive
itself went offline mid-check. Not retried since; worth one more real look if the Archive
comes back, but not something to keep blocking on.

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

**Evidence-type meanings written down explicitly, 2026-10-29, documentation only, no
schema change**: a third review pushed on what each `evidence_type` actually licenses
Baneward to say, since the six values (traditional/laboratory/animal_study/human_clinical/
regulatory/unspecified) were real from Phase 1.6 but their exact claim boundaries were only
implicit. Worth stating plainly so nothing downstream (UI copy, a future AI layer) drifts
into overclaiming: a traditional-use record means a use was documented, not that it's
clinically effective; a laboratory finding is about the compound, not the whole plant in a
human body; an animal study doesn't transfer its dose or effect to humans; a human clinical
finding is scoped to its own study population and conditions; a regulatory source documents
what that source says, not a universal rule; and the complete absence of any claim means
unreviewed, never "safe." Also a real, smaller gap worth tracking: the `verified` column is
still just a boolean, with no record of who verified a claim, when, or whether its original
source has since changed or gone offline (the FDA and ARS checklist dead-ends earlier in
this document are exactly the kind of source that can disappear). A real audit trail
(verifier, timestamp, source-still-reachable) is better than a boolean that quietly loses
that context — not built, worth doing before `verify_claim` gets used at any real scale.

## Phase 1.7 — Real Dr. Duke chemistry data, normalized after a real self-caught bug ✅ done 2026-10-29

Phase 1.6 deliberately scoped Dr. Duke's ingest to `ETHNOBOT` only and left the
chemical-level tables (`ACTIVITIES`, `AGGREGAC`, `CHEMICALS`, `FARMACY_NEW`) as real,
scoped future work. This phase did that work, resolving through `FNFTAX.csv` the same way
`ETHNOBOT` resolved through genus/species: **1,371 of our species match**, with real
documented bioactivities (chemical → activity/dosage/reference, via `AGGREGAC`) for the
chemicals they contain.

**Real bug found and fixed before anything was committed, not shipped and patched
after**: the first attempt stored one `claims` row per (species, chemical, bioactivity)
triple — **983,790 rows, 336MB**, with one species (*Tanacetum parthenium*, TAPA6) alone
picking up 8,460 rows, because a chemical's whole bioactivity profile got duplicated onto
every species that happens to contain that chemical. Caught this by checking the real
output before touching the live app or git, not by trusting the ingest script's own exit
code — rolled it back cleanly (`claims` table untouched throughout, back to the real
51,580-row count from Phase 1.6), reported it honestly, and redesigned before re-running
anything.

**Real fix**: a chemical's documented activities are a fact about the chemical, not about
any one species that happens to contain it — store each chemical and its activities
exactly once, link species to chemicals through a lightweight join table. Three new
tables (`chemicals`, `chemical_activities`, `species_chemicals`,
`app/src-tauri/src/db.rs`), rebuilt ingest (`data/ingest_duke_phytochemistry.py`).
Deliberately no `category` field on `chemical_activities` at all — a raw lab-documented
bioactivity (e.g. Antihepatotoxic, Anticarcinogenic — real activity names found during this
work that are the semantic *opposite* of what a naive "toxic" keyword search would
surface, a real trap avoided by not attempting automated poisonous/edible classification
here) is browsable reference data, not a claim about whether a given plant is safe. The
`claims` table and its verified-by-default-false rule are untouched by this phase.

**Real final numbers**: 3,001 distinct chemicals, 18,875 chemical-activity rows, 46,913
species-chemical links — median 15 chemicals per matched species, max 221, nothing close
to the first attempt's 8,460. Bundled database: 59MB (was 53MB after Phase 1.6). New
collapsible "Chemistry" section in the species detail view (`app/src/App.tsx`), one entry
per chemical with plant part and documented bioactivities including dosage/reference where
present. Verified against the real running app's live database the same way as every prior
phase: checked for new user claims first (none), updated the live copy's schema and data
surgically via `ATTACH DATABASE` rather than overwriting the file, resynced the bundled
resource afterward.

## Phase 1.8 — User-uploaded photos, and a real check on where to find more images ✅ done 2026-10-29

Frank's own framing: a photo is one of the top ways someone actually identifies a plant,
so it should be exactly as easy to add as a claim already is. Two real pieces of work came
out of that — closing the image-upload gap in the app itself, and checking whether the
78% of species with no usable image (27,650 of 35,326, confirmed by direct query) have a
real path to getting one.

**Real check on more images, done before building anything**: an outside suggestion named
iNaturalist, Wikimedia Commons, GBIF, Smithsonian, Pl@ntNet, and the Biodiversity Heritage
Library. Checked the two most promising directly via their live APIs rather than taking the
suggestion at face value — same discipline as every other source this project has touched:
- **iNaturalist**: real and live. A bounded test against 50 random zero-image species
  (live API, CC0/CC-BY only, research-grade) found at least one usable photo for **40 of
  50 (80%)**. The bulk Open Data S3 bucket is genuinely public (confirmed by listing it
  directly, no AWS key needed) and individual photos are fetchable at predictable URLs —
  real, worth building as a real pipeline, not done yet.
- **Wikimedia Commons**: API real, but a category query for a known species returned
  mostly Wikidata/Wikipedia UI icons mixed in with the one real photo — a real filtering
  problem to design around, not a blocker. The one real photo found was CC BY-SA 3.0
  (share-alike), confirming in practice that license needs explicit handling, not just in
  theory.
- **GBIF**: real, but for the one species tested, every image on the first results page
  was CC-BY-NC and sourced right back from iNaturalist's own bucket — for this use case it
  mostly re-surfaces iNaturalist with extra aggregator overhead, not obviously worth a
  separate pipeline.
- **Smithsonian Open Access, Pl@ntNet, Biodiversity Heritage Library**: not verified.
  Flagged honestly rather than vouched for secondhand.

Real next step, not done here: a proper iNaturalist ingest pipeline (license filtering,
taxonomic matching, dedup, provenance) — validated as worth building, not yet built.

**Real feature shipped this phase**: "Add your own photo," mirroring `add_claim` exactly.
Added `tauri-plugin-dialog` (already a real WayStation dependency, same version) for the
native file picker, and a `base64` crate for serving a local file to the frontend without
needing Tauri's asset-protocol scope config. Extended the real `images` table with
`source`, `verified`, `added_by`, `added_at`, `verified_by`, `verified_at`
(`data/migrate_images_schema.py`) — existing USDA rows backfilled as
`source='usda_plants'`, `verified=1` (institutional data, not a new claim); every new
upload inserts as `source='user_upload'`, `verified=0`. **Same rule as every text claim,
restated for a photo**: a user's photo is a claim that this is what the species looks
like, not a confirmed fact just because someone uploaded it — enforced in the Rust SQL
itself (`add_user_image` hardcodes `verified=0`; `verify_user_image`/`delete_user_image`
both gate on `WHERE source = 'user_upload'` so neither command can touch a bundled USDA
image, verified directly against the real database, not assumed from reading the code).

New "Your Photos" section in the species detail view, separate from the USDA public-domain
grid, each upload showing a verified/unverified badge with Verify/Remove actions. Verified
for real: `cargo check` and `npm run build` both clean, the live dev app rebuilt and kept
running through every change, and the actual SQL from every new command (insert, the
updated `get_species` query, verify, delete, including the ownership-guard case) run
directly against a scratch copy of the real database — not just trusted because Rust
compiled. Schema migrated on the master db, the live running app's db, and the bundled
resource, same three-step process as every prior phase.

## Phase 1.9 — The real iNaturalist image pipeline, prototyped on a bounded batch ✅ prototype done 2026-10-29

Phase 1.8 validated this was worth building (80% hit rate on a 50-species live-API test)
but didn't build it. This phase does — bounded to a real 100-species prototype first,
same discipline as every other source here (`build_phase0.py` before `ingest_full.py`):
prove the real approach end-to-end before deciding whether to scale to all 27,650
zero-image species.

**Real result, `data/ingest_inaturalist_images.py` against 100 zero-image species**:
**64 found and cached** (CC0/CC-BY, research-grade, exact-taxon-name-matched — a stricter,
more rigorous check than Phase 1.8's quick estimate, since this requires an actual
successful download, not just a nonzero search count). 36 had no eligible match.

**Real design decision, not just storing another live URL**: a community-sourced photo is
pointless for a grid-down app if it still needs the internet to render — same complaint
this project has already logged against USDA's own image URLs. So the actual bytes get
cached directly in a new `images.data BLOB` column (`data/migrate_images_schema.py`,
extended) rather than inventing a new file-bundling mechanism; the frontend gets a ready
data URI straight from `get_species` (`data_base64` field, `commands.rs`), reusing the
same base64-over-invoke approach Phase 1.8 already built for user uploads. Real measured
size: 64 images, 7.9MB total, ~124KB average — notably larger than USDA's own ~34KB
average (a different source, a different average, not interchangeable numbers).

**Trust tier kept honest, per this project's own "identification confidence is not safety
confidence" rule**: a research-grade iNaturalist ID means at least two independent people
agreed — a real signal, stronger than a single unreviewed upload, but still a community
identification, not USDA's own institutional tie. New "Community Photos (iNaturalist)"
section, visually and structurally distinct from both the USDA grid and "Your Photos" —
inserted as `source='inaturalist'`, `verified=0`, same unverified-by-default rule as
everything that isn't USDA's own data. `verify_user_image`/`delete_user_image` were
broadened from `source = 'user_upload'` to `source IN ('user_upload', 'inaturalist')` so a
household member can review and confirm (or remove) a community photo the same way they
review a claim — the guard still fully blocks either command from touching a `usda_plants`
row, re-verified directly against a scratch database after the change, not assumed.

**Real scaling math, not done yet**: at this run's real hit rate and average size, all
27,650 zero-image species would mean roughly **17,700 images, ~2.2GB** — a real, substantial
jump from the 67MB database today, and nowhere near the ~600MB estimate logged against
USDA's own smaller images (different average size, not the same number). iNaturalist's own
rate-limit guidance (~1 req/sec) also means resolving all 27,650 through this live
per-species API would take on the order of 7-8 hours sequential; a real full-scale pass
should likely use the bulk Open Data metadata dump instead (confirmed public and real in
Phase 1.8's own verification) rather than one API call per species. Not attempted here —
a real decision for Frank given the size jump, not something to default into.

## v2 — Discovery & UX pass (planned, not started)

**v1 is everything above through Phase 1.7**: a real working app, real USDA + Dr. Duke
data, search by name/synonym/characteristic, evidence-typed claims, documented chemistry.
v2 is committed here as its own real milestone — not a loose "someday" list — specifically
so the ideas raised by two outside reviews (Frank shared both, asked for a critical read
rather than a blind build) don't quietly disappear before there's a reason to build them.
What those reviews got right and is already real is folded into v1 above
(characteristics/synonym search data in Phase 1.5, the evidence-type claims model in
Phase 1.6); what's still just an idea is scoped into v2:

- **Identification wizard** — step through observable traits (flower color, leaf shape,
  habitat) to narrow down a species without knowing its name first. Phase 1.5 shipped the
  underlying data (200,872 characteristic rows across 2,058 of 35,326 species — 5.8%) and
  wired it into text search, but nobody's built the actual guided, step-by-step UI yet —
  real data, no wizard yet. **A third review (2026-10-29) added a real constraint that
  changes the design, not just the copy**: the wizard can't just warn that unindexed
  species get hidden and call it done — it needs to treat a missing characteristic value as
  a distinct `unknown` state, not the same as a documented `absent` (a plant with no
  recorded flower color is not the same as a plant documented as not flowering), and name
  search must still cover the full 35,326-species catalog even when characteristic search
  can only cover the 5.8% — so a dangerous species with no structured traits never becomes
  invisible just because it can't be found by trait.
- **Visual, filterable plant browser** — browse by trait instead of typing a search term.
  Same situation: the data exists, the browse-by-feature UI doesn't. Same `unknown`-vs-
  `absent` requirement applies, and any coverage count shown next to a filter has to be a
  real live query against the database, not a hardcoded "5.8%" that drifts as more
  characteristic data gets added later.
- **Curated dangerous-lookalike comparisons** — narrower and more useful than a general
  species-to-species comparison tool, per the same third review: a reviewed registry of
  specific dangerous pairs (poison hemlock vs. wild carrot/Queen Anne's lace is the obvious
  first entry, already this project's own running example), not an auto-generated
  "similar species" feature. Each pair's individual differentiators (stem markings, leaf
  shape, etc.) need their own source and review status — a verified pair-level
  relationship shouldn't imply every listed detail is independently confirmed. No
  comparison view exists yet; today a user has to open each species separately and
  remember the difference.
- **Field notes** — a place for a user's own observations tied to a sighting (location,
  date, photo), separate from the editorial claims system. Not designed yet, not just
  unbuilt. Keep the user's own proposed identification visibly separate from a reviewed
  determination, even after they pick a species from a candidate list — a field note is an
  observation, not a confirmed ID.
- **Kew's Medicinal Plant Names Services (MPNS)**, raised in the second review as a
  possible additional reference source — flagged early on as needing its own license
  check and never actually verified against the live service, unlike every other source
  in this document. Real open item, not closed either way.

v2 doesn't block Phase 2 or 3 below, and isn't scheduled ahead of them either — it's
committed as real scope, with no start date yet, so it survives past this session instead
of living only in chat history.

## Phase 2 — Local AI search integration

Wire up search/explain against Citadel's existing Off-Grid AI (Ollama) infrastructure — not
started, blocked on Phase 1's storage shape being real first (it is, as of Phase 1.7).

**Scope clarified 2026-10-29, a real ambiguity the third review caught in the line above**:
"scoped to already-verified entries" could mean two different things — (a) the AI may only
*search* species/claims that are already verified, or (b) the AI may search the full
catalog but any *safety conclusion* it surfaces may only draw on verified claims. Only (b)
is correct. (a) would create a real blind spot: a genuinely dangerous species whose claims
just haven't been human-reviewed yet would become invisible to search, which is worse than
surfacing it honestly with an "unreviewed" label. Concretely: the LLM is a semantic
parser, not the safety authority — it turns a free-text description ("tall plant, white
umbrella flowers, purple blotches on the stem") into a structured, schema-validated query
against the real characteristics/claims tables; Rust executes that query deterministically
and returns candidates plus what's verified/unverified/missing about each; the model never
gets to write SQL, invent a column, or flip a claim's verified status itself. The app has
to stay fully usable with Ollama absent or off — AI improves the search, it's never a
dependency for reaching the underlying data.

## Phase 3 — Tie into Citadel

Wire a launch point into Citadel's cockpit via `baneward://` (already registered in Phase
1, mirroring `waystation://`) — not started, the actual handshake with Citadel's cockpit is
the remaining work.

**Design note added 2026-10-29, not yet built or tested**: a deep link can arrive before
the React frontend finishes mounting, especially on a cold launch — a real class of race
condition in Tauri v2, not unique to this scheme. Plan is a small Rust-side queue: buffer
the incoming URI, hold it until the frontend emits its own `frontend-ready` signal, then
deliver it and wait for an explicit acknowledgment before clearing the queue. Two real
requirements once this gets built: delivery has to be idempotent (receiving the same URI
twice must not open duplicate views or re-run the same search), and cold launch (app not
running yet) and warm launch (already-running instance gets a second URI, same as
`tauri-plugin-single-instance` already handles for a second app launch) are genuinely
different cases that both need a real test, not just the cold-start path.

## Keeping this current

Same rule as the rest of the ecosystem: this file is the detailed, current source for
Baneward's own work. `citadel-ecosystem/MASTER_ROADMAP.md` gets updated to match when this
one moves, not the other way around.
