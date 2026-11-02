# Baneward — Roadmap

Real, dated, honest about what's done vs. planned — same discipline every other project in
the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem) uses.

## Where things stand (2026-11-01)

Repo created, name chosen (`Baneward` — "bane" = poison, as in wolfsbane/henbane, + "ward" =
guard/protect, naming the core red-alert-for-poison feature directly). **Phase 0 is fully
done**: all 35,326 real US species are enriched and sitting in a real local database, zero
failures, verified against live sources throughout — not assumed. Two of the three
originally-planned sources turned out not to hold up on direct verification; the plan was
corrected in response, not papered over. Phases 1 through 1.12 are also done: a real
standalone Tauri app (matching WayStation's stack), synonym/characteristic search data,
51,580 real ethnobotanical claims, 3,001 real documented chemicals with their lab
bioactivities, a real "add your own photo" feature, and real photo coverage for
**26,092 of 35,326 species (73.9%)** via iNaturalist, Wikidata, and Smithsonian pipelines —
including two real live-API rate-limiting incidents, the institutions that explicitly
forbid automated access, and a hard GitHub 2GB-per-file wall that forced a real
architecture split (lean core database + separate downloadable photo packs per source),
all logged honestly rather than hidden. **v2 — Discovery & UX pass is now fully
complete**: curated dangerous-lookalike comparisons (poison hemlock vs. wild carrot, 7
differentiators each independently checked against an authoritative reference), the
identification wizard — which also surfaced and fixed a real, previously-live bug: 18.5%
of the characteristics table (37,175 rows) were exact duplicates from Phase 1.5's own
ingest, now cleaned up — a visual browse-by-trait view reusing the wizard's own filter
design, and field notes (deliberately with no verified/unverified state at all — a
personal sighting, not a claim). The Kew MPNS open question was also closed with a real,
checked answer: no self-service bulk access exists, unlike every other source here. All
unverified by default, same rule throughout. **Phase 2 — local AI search is also done**:
a local Ollama model turns a free-text description into the same trait filters the wizard
and browse views already use, with every suggestion checked against real live data before
being used and never auto-applied — a real test run caught the model both inventing an
impossible value and inferring unstated facts, confirming why nothing it suggests is
treated as final. **Phase 3 — tying into Citadel is done**: a real tile lives on the
user's own actual running Citadel cockpit, verified live and screenshotted, not just added
to a mockup — and Frank himself confirmed the real click-through loads fine on his own
physical desktop, closing the one honest gap this remote session couldn't verify itself.
**Every phase of Baneward's own roadmap, Phase 0 through Phase 3, is now shipped and
confirmed.** A real next milestone is already logged, not started, revised against Frank's
own real prioritization: **v3 — Content Depth & Field Reach** — a plant-part/preparation
chart, a pasture/property survey for livestock-harmful plants, a patch map with a harvest
calendar, and medicinal cautions kept visibly separate from the traditional-use claims pile
— plus a real backlog of ten more items (photo-vs-reference comparison, household roles,
a verification-progress page, a lookalike quiz, state noxious-weed flags, a Garden Planner
link, high-contrast mode, bookmarks, cross-household claim sharing, alphabetical browse,
and an experimental photo-based AI identification feature explicitly gated on a real
accuracy test holding up first). See below for detail.

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

## Phase 1.10 — Full-scale image coverage: a real live-API failure, then the bulk dump ✅ done 2026-10-30

Frank's call: go ahead and scale to all remaining zero-image species. **Real honest
sequence, not a clean straight line**: the live per-species API (Phase 1.9's own script)
was launched first against all ~27,650 species, same mechanism that worked for the
prototype, just bigger. It worked cleanly for a while — 5,215 real images cached, 0
errors — but after ~18 hours of continuous querying, iNaturalist's API started returning
sustained 429s (1,576 of ~9,750 requests, a real and growing fraction, not a blip). The
degraded rate stabilized rather than collapsing, but projected out to **~2.5 more days**
for the remaining species — a real, substantial cost nobody had signed up for. Stopped the
live-API run there rather than let it grind for days; its 5,215 real images stayed
committed, nothing lost.

**Real switch to the bulk Open Data dump**, verified column-by-column before committing to
anything: `taxa.csv.gz` (39MB), `observers.csv.gz` (20MB), `observations.csv.gz` (13.7GB),
`photos.csv.gz` (21.1GB) — real sizes confirmed against the live bucket, real columns
confirmed via byte-range peeks before downloading the two big files in full (`tar`-listing
a multi-GB gzip stream isn't actually cheaper than downloading it, so a byte-range peek at
just the header was the real way to check structure first). A quick 100MB throughput test
(≈4.7MB/s real, not assumed) put the full ~35GB download at roughly 2 hours — a measured
number, not a guess, before committing to it.

**`data/ingest_inaturalist_bulk.py`, four real stages, each one streaming pass, each
resumable**: matched 15,362 of the 17,220 still-unresolved zero-image species against an
active iNaturalist `taxon_id` (`taxa.csv.gz`); streamed all ~280M rows of
`observations.csv.gz` once (14.2 min) to keep only research-grade observations of a
matched taxon (8.2M kept, covering 12,365 of the 15,362 — a real, honest ceiling, not every
matched taxon has a research-grade observation at all); streamed all ~500M rows of
`photos.csv.gz` once (25.6 min) to pick the first CC0/CC-BY photo per taxon (9,580
resolved); fetched each one's real bytes directly from S3's static photo URLs — the same
URLs the live-API script already used, not the throttled REST endpoint, so this stage hit
**zero rate-limit errors** across all 15,362 species checked. Real end-to-end run time:
about 2 hours download + 40 minutes processing + a few minutes of fetching, matching the
~3-hour estimate given before starting, not the 2.5 days the live-API path was facing.

**Real final numbers, combining both runs**: **14,795 total iNaturalist-sourced images**
(5,215 from the live-API run before it was stopped + 9,580 from the bulk run), real average
131.6KB each, 1.95GB of real cached image bytes, zero insert errors across the whole
session. **22,470 of 35,326 species (63.6%) now have at least one usable image**, up from
7,676 (21.7%) before this phase — real species still with none: 12,856, down from 27,650.
Spot-checked: real JPEG magic bytes confirmed on a sample row, a real uppercase `.JPG`
extension variant found in the wild and confirmed already handled by the existing
lowercase-normalizing Rust code, no new code path needed.

**Real cost worth stating plainly**: the master database is now **1.9GB** (was 67MB before
this phase) and the bundled app resource grew to match. Pushing this to GitHub via Git LFS
consumes roughly 19% of the account's 10GB free LFS storage quota in this one file — a
real, current constraint on how much further this specific approach can scale before
needing a paid LFS tier or a different distribution strategy (e.g. the tiered
core/regional/complete download modes already logged as an idea against the original
USDA image-caching gap, which now applies here too).

Live running app and bundled resource both resynced and verified healthy (same three-step
process as every prior phase) before any of this was pushed.

## Phase 1.11 — Two more real sources, after confirming most of GBIF's hosts can't be used

Frank's question after Phase 1.10: "is there a way to get to 100%?" Honest answer, backed
by the real numbers the bulk pipeline left behind: no, not fully — roughly 1,900 of the
remaining species have no matching taxon on iNaturalist at all, ~3,000 have a taxon but no
community-verified observation, and ~2,800 have a verified observation but no permissively
licensed photo. That's a real floor, not a search problem. Frank asked to pursue whatever
sources would actually help anyway.

**Checked GBIF as a broader institutional source before building anything — found a real
reason not to use most of it.** GBIF aggregates image records from dozens of independent
herbaria and museums, not one bulk-friendly host like iNaturalist. Checked robots.txt and
access policy for the hosts that showed up in real sample results: California Academy of
Sciences explicitly states automated bulk access is not permitted, even on content its own
metadata marks CC0. Naturalis's robots.txt explicitly disallows the `anthropic-ai` user
agent by name. New York Botanical Garden returns 403 Forbidden on its own robots.txt. Paris's
natural history museum sits behind an active Cloudflare bot challenge. Only Smithsonian
(`collections.nmnh.si.edu`) checked out clean — permissive robots.txt, a real image fetched
successfully. **Scoped GBIF usage to Smithsonian only, by design, not by oversight.**

**Also checked Wikimedia Commons' own free-text search before trusting it, and found a real
accuracy problem, not just a coverage one.** A quoted-phrase search for "Arthrocnemum
subterminale" returned a photo titled for the unrelated genus *Arthroceras*; "Rhizocarpon
lavatum" (a lichen) returned a figure from an entirely different fungal order. MediaWiki's
search does fuzzy relevance matching, not exact identification — unsafe to build on directly
for a database whose whole point is correct identification. Switched to Wikidata's
structured `P225` (taxon name) → `P18` (image) property instead, which isn't pure free text,
but still cross-checked each candidate's own filename for the genus before accepting (the
*Arthroceras* mismatch turned out to trace back to a bad link on the Wikidata item itself,
not just bad search — real insurance against the same kind of error wherever it originates).

**Real measured yield on a 25-species sample of species the iNaturalist pipeline couldn't
resolve**: Wikidata 16%, Smithsonian 12%, some overlap — nowhere near iNaturalist's own
hit rate, because what's left is disproportionately lichens, mosses, and rare local
endemics that are thinly documented everywhere, not just on one platform. A first pass also
found Wikidata's `P18` images average **2.2MB** (full-resolution Commons originals) against
every other source's ~100-250KB — fixed by requesting Commons' own 500px thumbnail
(`iiurlwidth`) instead, averaging 91KB after the fix; the 8 oversized rows from before the
fix were deleted and correctly re-resolved, not left in.

**Real full-scale run, `data/ingest_secondary_images.py` against all 12,788 remaining
zero-image species**: GBIF's occurrence-search endpoint started sustained rate-limiting
partway through — the same kind of real-world throttling iNaturalist's REST API hit in
Phase 1.10, this time against a different API. Unlike that first time, retry/backoff was
built in from the start (the lesson was fresh), so this run never lost data or stalled —
it just ran slower than planned, roughly 21.8 hours instead of the ~4.6-hour clean-rate
estimate. **807 Wikidata images + 2,747 Smithsonian images found, only 10 real errors
(transient network resets/timeouts) out of 12,788 species checked, all ten safely retryable
on a future run since they were never written to the "no match" cache.**

**Real final numbers**: **26,092 of 35,326 species (73.9%) now have at least one usable
image**, up from 22,470 (63.6%) before this phase. Database grown to **2.7GB** (was 1.9GB).

**Real correction to Phase 1.10's own cost estimate, found while preparing to push this
phase**: that phase said pushing its database consumed "roughly 19%" of the account's 10GB
free Git LFS quota — true only for that one version in isolation. GitHub LFS keeps every
historically pushed version of a tracked file by default, with no automatic pruning; the
real cumulative total across all 7 versions pushed so far for this one file is **2.33GB**,
and this phase's own version adds another **2.89GB** — **5.22GB, 52% of the free quota,
from this single file's version history alone.** Flagged to Frank before pushing rather
than discovered later, since it's a real, current constraint on how many more full-database
replacements this project can push before needing either a paid LFS tier, a history rewrite
to reclaim old versions (a real, deliberate, disruptive decision — not done unilaterally),
or a genuinely different distribution strategy for images going forward.

## Phase 1.12 — Split the image cache out of the bundled database; a real 2GB wall, not just a quota one

The actual push attempt for Phase 1.11 didn't fail on quota — it failed outright. GitHub
rejected the file with **"Size must be less than or equal to 2147483648"**, exactly 2GiB:
a hard per-file Git LFS limit, separate from and more immediate than the 10GB account
quota. Our file was 2.89GB. No amount of quota headroom fixes a per-object ceiling — this
needed a real architecture change, not a decision about how much more to spend.

Frank's call: do the real fix (a tiered core/extra-downloads split) rather than a stopgap
that just buys a little more room under the same ceiling.

**`data/split_image_packs.py`**: pulled the cached photo bytes (iNaturalist/Wikidata/
Smithsonian, Phases 1.9-1.11) out of the main database into one file per source — each
lands comfortably under the 2GB limit on its own (iNaturalist 1.96GB, Smithsonian 0.79GB,
Wikidata 0.08GB), a natural boundary, not an arbitrary chunk size. The main database keeps
every image's full metadata (url, photographer, source, verified, etc.) — only the heavy
`data` BLOB moves out, replaced with `NULL` until a pack is downloaded. Real result:
**main database back down to 70MB** (was 2.89GB), the same order of magnitude as Phase
1.8, before any of this image-caching work began.

**New Rust commands (`commands.rs`)**: `image_pack_status` reports each source's real
total/downloaded counts; `download_image_pack` fetches a source's pack file (if not
already cached locally) from this repo and merges it into the live database with the
same `ATTACH DATABASE` + `UPDATE` pattern used all session for surgically merging new data
— verified correct by running the exact SQL against a scratch copy of the lean database
before trusting it in the real app (822 Wikidata rows: 822 NULL before, 0 NULL after, real
JPEG bytes confirmed on a sample row). Added `ureq` as a new dependency for the actual
HTTP fetch — a blocking, synchronous client, matching every other command in this codebase
rather than introducing an async runtime for one feature.

**Frontend**: generalized the single iNaturalist-only "Community Photos" section into one
per real source present (iNaturalist, Wikidata/Commons, Smithsonian), each with its own
real attribution copy. Where a species has photos from a pack that isn't downloaded yet,
shows a real count and an explicit "Download the `<source>` photo pack (~size)" prompt
instead of a broken or endlessly-loading image — the old `data_base64 ? <img> : <Loading>`
fallback used to be accurate (every row had its bytes inline already); now a permanent
`null` is an expected, common state, not a transient one, and the UI says so honestly.

**Real care taken not to regress the already-working live app**: the live app's own
database already has every image's bytes inline from Phases 1.9-1.11 — splitting the
*master* database for the bundled installer must never mean splitting (and thereby
blanking) the *already-populated* live one. Verified directly rather than assumed: all
18,417 non-USDA images in the live app's database still have real, non-NULL bytes after
this phase — nothing lost. The live app only needed its binary and frontend rebuilt to
pick up the new commands; its actual data was never touched.

**Not yet done**: the pack files themselves aren't pushed yet (next, right after this).
No UI exists yet to download all three packs at once, or to see pack-download progress
mid-transfer (today's version is a blocking call with a plain "Downloading…" state — real
and functional, not polished). The iNaturalist pack is already close to the 2GB ceiling
(1.96 of 2.0GB) — real future growth of that specific source will need to either split it
further (e.g. by first letter of genus) or stop growing it past this point.

## v2 — Discovery & UX pass ✅ complete 2026-11-01

**v1 is everything above through Phase 1.7**: a real working app, real USDA + Dr. Duke
data, search by name/synonym/characteristic, evidence-typed claims, documented chemistry.
v2 is committed here as its own real milestone — not a loose "someday" list — specifically
so the ideas raised by two outside reviews (Frank shared both, asked for a critical read
rather than a blind build) don't quietly disappear before there's a reason to build them.
What those reviews got right and is already real is folded into v1 above
(characteristics/synonym search data in Phase 1.5, the evidence-type claims model in
Phase 1.6); what's still just an idea is scoped into v2:

- **Identification wizard** ✅ **done 2026-11-01** — see its own write-up right after the
  lookalike-comparison one above.
- **Visual, filterable plant browser** ✅ **done 2026-11-01** — see its own write-up after
  the identification wizard's.
- **Curated dangerous-lookalike comparisons** ✅ **done 2026-11-01** — see its own write-up
  right after this list.
- **Field notes** ✅ **done 2026-11-01** — see its own write-up right after the
  browse-by-trait one above.
- **Kew's Medicinal Plant Names Services (MPNS)** ✅ **checked directly 2026-11-01, real
  answer, closed as not usable via this project's normal pattern.** Checked Kew's own MPNS
  page and its data Terms of Use directly rather than leaving it open any longer. Real
  finding: MPNS doesn't offer the kind of self-service bulk download or public API every
  other source in this document has had — its own page lists "we can supply subsets of
  MPNS data tailored for use in your own database" as a bespoke service, not a documented
  endpoint, and the only self-service access is an interactive portal for one-plant-at-a-
  time lookups. Kew's Terms of Use state dataset *metadata* is CC BY, but that's a
  different claim from "the underlying data is freely bulk-reusable" — the license that
  actually matters for an ingest isn't published anywhere self-service. Real next step, if
  this is ever worth pursuing: someone emailing mpns@kew.org to request a real data subset
  and agree real terms — a human relationship, not an automated ingest, and not something
  to initiate without Frank's own explicit decision to pursue it. Closed as a real, honest
  answer rather than left ambiguous.

v2 doesn't block Phase 2 or 3 below, and isn't scheduled ahead of them either — it's
committed as real scope, with no start date yet, so it survives past this session instead
of living only in chat history.

### v2's first real deliverable: curated dangerous-lookalike comparisons ✅ done 2026-11-01

**Real schema, deliberately not an auto-generated "similar species" feature** — the data
model itself guards against that, not just the UI copy. `lookalike_pairs` holds a specific,
human-entered pair with its own `risk_level` (fatal/severe/moderate/mild) and overall
summary; `lookalike_differentiators` holds each individual distinguishing feature under a
pair, each with its **own** `verified` flag, reliability notes, and source — a verified
pair never implies every differentiator under it is independently confirmed, the real
problem an outside review flagged with a generic "verified relationship" design. Same
unverified-by-default rule as claims and images throughout (`db.rs`).

**Real seed content, not placeholder text** — poison hemlock (*Conium maculatum*, COMA2)
vs. wild carrot/Queen Anne's lace (*Daucus carota*, DACA6), this project's own running
example since Phase 0. Given the real stakes (this is literally "how do I tell these two
plants apart so I don't die"), every differentiator was checked against a real authoritative
source before being written down — not generated from memory, same discipline as every
other content addition this project has made. Two real sources, fetched and read directly:
King County, WA's own Noxious Weed Control Program page (government source, for poison
hemlock's own description) and Illinois Wildflowers (a well-regarded botanical reference,
for wild carrot's). Real correction this surfaced versus the popular "a single purple
floret in the center always marks Queen Anne's lace" claim repeated across many casual
foraging sites: Illinois Wildflowers' own text says that floret is only "sometimes" present
and "very rarely" affects every flower in the umbel — included as a real differentiator,
but explicitly flagged as unreliable alone rather than oversold as a reliable marker.

**Seven real differentiators seeded, each independently verified**: stem markings (the
single most reliable one — present at every growth stage per King County), stem hairiness,
crushed-leaf/stem odor, mature height, flower-cluster center color, bracts, and root —
each with its own reliability caveat (e.g. root and odor both require handling the plant,
which carries a real skin-contact risk with poison hemlock specifically, so both are
flagged as corroborating tests, not first-glance or standalone ones).

**Real UI**: a species with a known dangerous lookalike shows a prominent red-bordered "⚠
Often confused with" warning near the top of its detail view (before images, before
claims) — real risk-level badges, unreviewed pairs marked as such. Clicking opens a
dedicated side-by-side comparison view: both species' names, a shared safety caveat ("no
single feature below is a safe identification method on its own"), and a table of every
differentiator with its own verified/unverified status, reliability notes, and source —
plus the same add/verify/remove mechanism as claims, so a household member can add a new
differentiator (starts unverified) or review an existing one.

Verified for real: `cargo check` and `npm run build` both clean, the real SQL for the
"lookalikes for this species" query checked from both species' own perspective (`COMA2`
correctly shows wild carrot as its lookalike, `DACA6` correctly shows poison hemlock back —
the join has to work symmetrically, not just one direction), the live dev app rebuilt and
stayed running through every change, schema and seed data applied to the master db, the
live running app's db, and the bundled resource, same three-step process as every prior
phase.

### v2's second real deliverable: the identification wizard ✅ done 2026-11-01

The actual reason v2 exists — the original outside review's own question was "what if I
don't know the name, how do I find it?" Phase 1.5 shipped the underlying data
(characteristic rows for 2,058 of 35,326 species) but nobody had built the step-by-step
UI. This does.

**Real step selection, grounded in the actual data, not assumed**: checked real
per-characteristic coverage and value distributions before picking anything. Most
characteristic *names* in the table are yes/no agricultural-use flags (Christmas Tree
Product, Propagated by Bulb) — useless for visual identification. Five real fields had both
strong coverage (1,950-2,060 of the 2,058 species with any data) and a small, clean set of
real values: Flower Color (8 values), Foliage Color (6), growth form/"Shape and
Orientation" (11), Bloom Period (12), Fruit/Seed Color (9) — these became the wizard's
fixed step sequence.

**The one rule the schema has to get right, per the design requirement already logged
here**: a species with no recorded value for a trait must stay a candidate when that trait
is selected — missing data is a real `unknown` state, never silently the same as
"confirmed not this." The real SQL: a species survives a selection if it either has no row
for that characteristic at all, or has a row whose value matches what was picked. Verified
directly against the database before trusting it in the app — confirmed a white-flowered
species is correctly excluded after selecting "Flower Color: Yellow," and confirmed a
species with zero flower-color data is correctly kept as a candidate, not silently dropped.

**Real bug found and fixed along the way, not introduced by the wizard but surfaced by
it**: building the wizard's "how many of your answers does this species actually confirm"
counter turned up a live, pre-existing data bug — one species (tall fescue, SCAR7) had
every one of its ~80 real USDA traits duplicated 25 times over (2,001 rows for one
species), left behind by Phase 1.5's own ingest. Checked the real scope before fixing
anything: 200,872 total characteristic rows, only 163,697 actually distinct — **37,175
duplicate rows (18.5%) were already live**, meaning any species detail page showing
duplicated species had been quietly repeating facts in its Characteristics section this
whole time, not just a wizard-building artifact. Fixed at the source
(`data/dedupe_characteristics.py`, keeps one row per real distinct
(species, name, value) triple) rather than just working around it in the wizard query —
though the wizard's own "confirmed" count was also hardened to `COUNT(DISTINCT
characteristic name)` regardless, so it can't be thrown off by future data issues either.

**Real UI**: a "🌿 Don't know the name? Identify by what it looks like" entry point next
to the search box. Each step shows real, live option counts (queried against whatever
candidates survived prior answers, never a static list) plus an explicit "I don't know /
skip this" choice and a "see candidates so far" escape hatch at any point. Results are
sorted by how many of the user's answers a species actually has confirmed data for — but a
species with zero confirmed matches is never excluded, and the UI says plainly that "0
confirmed" means unindexed, not ruled out.

Verified for real: `cargo check` and `npm run build` both clean, the real database
deduplication confirmed (200,872 → 163,697 rows, exact match between the master db and the
live app's own copy), the filter logic spot-checked directly (mismatch excluded, unknown
kept, confirmed-count correctly bounded at or below the number of real selections made —
not the inflated 25-per-row figure the duplicate data was producing before the fix), the
live dev app rebuilt and stayed healthy through every change.

### v2's third real deliverable: visual browse-by-trait ✅ done 2026-11-01

The wizard is guided and sequential; this is the exploratory counterpart — all filters
visible at once, any combination, any order, no imposed question sequence. Built to reuse
the wizard's own backend almost entirely: the same `(no data for this trait OR matches the
selected value)` filter rule, the same confirmed-vs-unknown distinction, the same
`wizard_search` command for results — the only genuinely new piece is `browse_facets`,
which returns live option counts for every facet at once rather than one "next question"
at a time, each computed against the candidates implied by every *other* facet's current
selection so switching one facet's own value still shows real counts for all its options
(standard faceted-search behavior).

**Real facet set, checked the same way as the wizard's**: the wizard's own 5 plus 3 more
with the same real coverage/clean-value-count bar (1,500+ species, a small real value set)
— Growth Form, Active Growth Period, Foliage Texture. **Deliberately excluded**: the
`Toxicity` field, despite having decent coverage (1,977 species) — it's an NRCS
agricultural/conservation judgment, not a verified human-safety claim (see `db.rs`'s own
longstanding note on `characteristics`), and turning it into a browsable filter would
visually dress it up as equivalent to the real `claims` system. It stays visible in a
species' own Characteristics section, just not promoted into a filter chip.

Verified the real cross-facet filtering directly before trusting it: selecting "Foliage
Texture: Coarse" and checking the live Growth Form option counts came back correctly
narrowed (every count ≤ its real unfiltered total, confirming the filter is actually
applying, not just redrawing the same numbers).

Verified for real: `cargo check` and `npm run build` both clean, the live dev app rebuilt
and stayed healthy through the final edit. No new data or schema needed — this phase is
pure backend/frontend logic reusing Phase 1.5's existing characteristics data and the
wizard's own filter design, so nothing needed resyncing to the live app or bundled
resource.

### v2's fourth and final real deliverable: field notes ✅ done 2026-11-01 — **v2 complete**

A real, deliberate structural difference from every other user-contributed table in this
project: `field_notes` has no `verified` column at all. A field note is a personal
sighting, not a fact proposed for review — there's nothing to verify, and giving it a
review state would risk it quietly being treated like a claim. `get_species` keeps it in
its own section, never merged into `claims`. `species_symbol` is nullable on purpose: a
note can exist before anyone knows what the plant actually is, matching the real original
ask ("a place for a user's own observations tied to a sighting... separate from the
editorial claims system").

**Real UI, two real entry points**: a standalone "My Field Notes" log (new entry button
next to the wizard/browse ones) showing every note across every species chronologically,
including unlinked ones labeled "Unidentified," with an add-note form that doesn't require
a species link at all. And a "Field Notes" section on each species' own detail page,
scoped to that species, for notes added once an ID is known or suspected. Both forms share
the same real fields: observation (free text), location (optional), and the real date
observed (not just when the note was added to the app — `observed_at` vs `added_at` are
kept genuinely separate).

Verified the real SQL directly against a scratch database before trusting it: inserted a
species-linked note and an unlinked one, confirmed the standalone log's join correctly
resolves the linked note's species name and leaves the unlinked one's species fields null,
confirmed the species-scoped query only returns that species' own notes, confirmed delete
removes the right row. `cargo check` and `npm run build` both clean, schema applied to the
master db, the live app's db, and the bundled resource, live dev app rebuilt and stayed
healthy.

**v2 — Discovery & UX pass is now fully done**: identification wizard, visual
browse-by-trait, curated dangerous-lookalike comparisons, and field notes all shipped,
plus the Kew MPNS question closed with a real, checked answer rather than left open. Every
item from the original two outside reviews that survived critical review has either
shipped or been closed with a real, honest finding — nothing from that list is still
sitting ambiguous.

## Phase 2 — Local AI search integration ✅ done 2026-11-01

Wire up search against Citadel's existing Off-Grid AI (Ollama) infrastructure. Checked
real environment state before starting, rather than assuming: Ollama was genuinely
installed and running on this machine (`localhost:11434`, two real models available,
`llama3.2:3b` and `llama3:8b`) — Phase 2 was actually startable immediately, not blocked
on setup.

**Scope clarified 2026-10-29, a real ambiguity the third review caught**: "scoped to
already-verified entries" could mean (a) the AI may only *search* already-verified
species/claims, or (b) it may search the full catalog but any *safety conclusion* it
surfaces may only draw on verified claims. Only (b) is correct — (a) would hide a
genuinely dangerous species whose claims just haven't been reviewed yet, worse than
surfacing it honestly as unreviewed.

**Real, maximal code reuse**: the AI's entire job is turning free text into the exact same
`{characteristic, value}` selection shape the wizard and browse views already use —
`ai_parse_description` returns `Vec<WizardSelection>`, and the frontend feeds that straight
into the existing browse view as pre-applied, fully editable filter chips. No new results
UI, no new database queries beyond building the real vocabulary live from the
`characteristics` table (same `BROWSE_FACETS` list, not a separate hardcoded one that could
drift). `ureq` and `serde_json` were already dependencies from Phases 1.12/1.9 — zero new
ones needed.

**Real hallucinations caught while building this, not assumed as a risk**: a live test run
against `llama3.2:3b` had the model invent `{"characteristic": "Foliage Color", "value":
"None"}` — "None" was never a real value in the vocabulary it was given. The validation
gate (every returned pair checked against real, live `SELECT DISTINCT value FROM
characteristics WHERE name=?` results before being used) caught this for real, not as a
theoretical safeguard. A second real test surfaced a subtler problem the value-level check
*can't* catch: given "a thicket-forming plant with yellow flowers and gray-green foliage,
blooming in late spring," the model correctly extracted 4 real, explicitly-stated facts —
but also inferred `Fruit/Seed Color: Yellow` and `Active Growth Period: Spring`, neither of
which the description actually said. Both were individually real, valid values (so the
validation gate let them through), just not things the user had stated. This is exactly
why the result is never auto-executed as a final answer — it lands in the browse view as
removable chips the user reviews before anything is treated as a real filter, not a
"the AI has spoken" result.

**The real safety boundary, enforced structurally, not just in the prompt**: the model
never touches SQL, a database connection, or a claim's verified status — its only output
is JSON text, parsed and checked against real data before any of it becomes a query. The
app stays fully usable with Ollama absent or off entirely — the wizard and browse views
(and search) work identically either way; the AI command simply errors cleanly ("couldn't
reach the local AI — is it running?") and the UI points back to the manual tools, never a
hard dependency for reaching the underlying data.

Verified for real: `cargo check` and `npm run build` both clean, a full end-to-end run
against the live database and the real running Ollama instance (not just a unit-level
mock) — real model output, real validation pass/fail, confirmed directly before trusting
the design. New entry point: "🤖 Describe what you saw (local AI)," clearly labeled as
local, not a cloud service, with the scope and limits stated plainly in the UI itself, not
just in this document.

## Phase 3 — Tie into Citadel ✅ done 2026-11-01

**Real correction to the 2026-10-29 design note below it**: that note assumed a Citadel
deep link might carry a real payload (a search query) and designed a buffering/
acknowledgment queue around that. Checked the actual, real, already-deployed Citadel
cockpit source (`~/citadel/appdata/cockpit/index.html`, the user's own live home server,
not a mockup) before building anything — the real pattern every existing ecosystem tile
uses, including WayStation's own shipped `waystation://open`, is a bare `action://open`
with **no payload at all**. `handleModuleClick` just does `window.location.href = action`
and lets the OS hand off to the registered app. The speculative buffering/idempotent-
delivery design was solving a problem that doesn't exist in the real integration pattern —
not built, because building it would have been real complexity for a payload Citadel never
actually sends. If a future Citadel version adds deep search links, this is the first
place to revisit.

**Real work done, on the user's actual live Citadel cockpit, not a copy**: added
Baneward's own tile to `coreModules` (`action: "baneward://open"`, real description,
placed next to the Garden Planner tile) and its own entry to the health strip, marked
`unmonitored: true` with the same honest reasoning WayStation's own entry already used — a
static cockpit page genuinely cannot observe whether a native desktop app is running, so
it shows "UNKNOWN," never a fabricated status. Also generalized `handleModuleClick`'s
URI-scheme check from a literal `'waystation://'` string match to any non-`http` custom
scheme, so Baneward's tile (and any future ecosystem app's) works without needing this
function edited again. Verified live and screenshotted against the real running cockpit at
`localhost:8085` (an actual nginx container serving this exact file) — the tile renders
correctly, matching every other card's layout, with the real "UNKNOWN" health badge.

**Real limitation found and reported honestly, not glossed over**: tried to verify the
actual cold-launch and warm-launch (already-running, second `baneward://open` click)
behavior end-to-end via `xdg-open baneward://open` at the OS level. Both attempts left the
process stuck in GTK/WebKit startup (disk-sleep state, ~50MB RSS, never completing). Before
concluding this was a real Baneward bug, tested whether the same thing happens to
WayStation — the already-shipped, working reference implementation using the identical
`tauri-plugin-single-instance` + `tauri-plugin-deep-link` pattern — by launching a fresh
disposable WayStation instance the same way. **It showed the identical stuck-in-startup
behavior.** That's real, direct evidence this is a shared environment limitation of this
specific remote/sandboxed dev session (most likely an incomplete display/compositor stack
for WebKitGTK), not a defect introduced by Baneward's own Phase 3 work — but it also means
the actual cold/warm-launch and single-instance-focus behavior genuinely was **not**
confirmed end-to-end in this session, and shouldn't be claimed as verified. What *was*
confirmed directly: the OS-level scheme registration itself is real and correct
(`xdg-mime query default x-scheme-handler/baneward` resolves to the real
`baneward-handler.desktop` file), and the Rust side needs no new code at all beyond what
Phase 1 already built, since there's no payload to parse — matching WayStation's own
equally minimal, already-working implementation exactly.

**Closed for real, 2026-11-01**: Frank clicked the real "Wild Plant Database" tile on his
own actual physical desktop and confirmed it loads fine — the one thing this remote
session genuinely couldn't verify itself. That's every phase on Baneward's own roadmap
now shipped and confirmed, Phase 0 through Phase 3.

## v3 — Content Depth & Field Reach (planned, not started)

First drafted 2026-11-01 from an honest self-assessment once every build phase shipped —
revised 2026-11-02 against Frank's own real prioritization, which supersedes mine. The
real diagnosis underneath both versions is the same: the *skeleton* is complete and
well-engineered, but the safety-critical *content* is still thin, and the platform has a
real gap for the actual use case. Committed here the same way v2 was — real scope, not a
loose list that only lives in chat.

**The four strongest, Frank's own ranking:**

- **Plant-part and preparation chart.** A grid showing which part of a plant is edible,
  poisonous, or edible only after processing — pokeweed, acorns, and elderberry each
  depend on the part, the growth stage, or the prep. Possibly the biggest real safety gap
  left after the poison data itself. Real, honest scoping: the *display* mechanism is
  mostly reuse — `claims.plant_part` already exists and is already populated — but the
  actual part-by-part *safety data* (e.g. "raw poisonous, cooked edible," not just "this
  part was used traditionally") mostly doesn't exist yet in a structured form. Dr. Duke's
  claims record traditional uses by plant part, not a clean edible/poisonous/
  edible-after-processing state machine — real content work, same sourcing discipline as
  the lookalike pairs, not just a UI pass.
- **Pasture or property survey.** Walk a pasture or lot, log each plant found, get back a
  list of anything harmful to livestock. Builds on field notes (real, already shipped) plus
  a real new field this doesn't have yet: claims currently have no "who it affects"
  dimension (human/livestock/pet/general) — `category='poisonous'` today doesn't
  distinguish "toxic to goats" from "toxic to people." A real, honest schema gap to design
  around, not just a query away. Fits the ecosystem's own ranch-country context.
- **Your own patch map and harvest calendar.** Optional GPS on field notes, plus a
  reminder when a logged patch comes back into season. Real schema need: `field_notes` has
  no location columns yet (nullable lat/lng, kept genuinely optional). The "comes into
  season" part can reuse real, already-ingested data — Bloom Period and Fruit/Seed Period
  Begin/End are real USDA characteristics already in the database for the ~5.8% of species
  that have them — but "reminder" in a desktop app with no push notifications realistically
  means "flagged when you open the app near the season," not a true background alert;
  worth deciding explicitly, not assuming. "Locations stay private" is already true by
  construction — nothing in this app syncs anywhere today.
- **Medicinal cautions.** Sourced warnings about pregnancy, drug interactions, and
  dangerous doses, kept as their own category so they can't get buried among ~200
  traditional-use claims for one species (castor bean's own real count). Real open design
  question: a new `claims.category` value (e.g. `caution`), or a fully separate small
  table the way `lookalike_pairs` got its own table instead of overloading `claims` —
  worth deciding deliberately, given the same real reasoning that split lookalikes out in
  the first place (a thing that must never get quietly buried needs its own real
  visibility, not just a tag on a pile).

**The rest of the backlog, not yet prioritized, logged so none of it quietly disappears:**

- Side-by-side comparison of a user's own photo against a candidate species' reference
  photos and its known lookalikes — a real, natural extension of both "Your Photos" and
  the lookalike-comparison view, once there's more than one lookalike pair to compare
  against.
- Household roles — only specific people can verify a claim, anyone can add one. Real,
  honest gap this would close: there is no user-account system at all today;
  `added_by`/`verified_by` are free-text strings, not real identities — this is a bigger
  addition than it sounds, not a small toggle.
- A progress page showing how many claims are verified — makes the real, currently-mostly-
  invisible review backlog (51,580 claims, nearly none reviewed) visible instead of buried.
- A lookalike quiz — real, but wants more than one lookalike pair to be worth building;
  depends on the lookalike-curation item above actually happening first.
- A noxious-weed flag sourced from real state weed lists — a new external data source,
  needs the same real license/access verification discipline as every other source in this
  document before anything gets ingested, not yet checked.
- A Garden Planner link: identify weeds in the user's own raised beds, and flag plants
  toxic to chickens near the coop. A real, concrete tie to Citadel's own `garden.html`
  (the same file Phase 3 just added Baneward's own tile next to).
- A high-contrast mode readable in direct sunlight — real, standalone, no data dependency.
- Bookmarks for frequently-checked species — real, small, standalone.
- Browse the full catalog alphabetically, not just via search-by-name or trait filters —
  real and genuinely small: a plain `ORDER BY common_name` list reusing the exact same
  result-row rendering already built for search/wizard/browse results, no new schema, no
  new backend concept. The cheapest real item in this whole list.
- Sharing verified claims between trusted households — imports arrive unverified until a
  human reviews them, the exact same unverified-by-default discipline this whole project
  already runs on, just applied across installs instead of within one. Real overlap with
  the "how does anything sync between installs" question already open from the
  field/mobile-companion idea — worth answering once, not twice.
- Photo-based identification suggestions from a local AI model — the experimental, most
  real-risk item here, and Frank's own stated condition is the right one: build it only if
  a real accuracy test holds up first, same evidentiary bar the text-based AI search was
  held to before it shipped (that one got built after live tests against real data showed
  it working, with real failure modes caught and designed around — this one needs the
  equivalent real test before any commitment to build it, not an assumption that a vision
  model will behave as well as the text one did).

No start date yet on any of this — logged here so none of it quietly disappears, the same
reason v2 got written down before it was built.

## Keeping this current

Same rule as the rest of the ecosystem: this file is the detailed, current source for
Baneward's own work. `citadel-ecosystem/MASTER_ROADMAP.md` gets updated to match when this
one moves, not the other way around.
