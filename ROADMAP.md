# Baneward — Roadmap

Real, dated, honest about what's done vs. planned — same discipline every other project in
the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem) uses.

## Where things stand (2026-10-27)

Repo created, name chosen (`Baneward` — "bane" = poison, as in wolfsbane/henbane, + "ward" =
guard/protect, naming the core red-alert-for-poison feature directly). **Phase 0 is real and
done for its core scope**: the USDA PLANTS data pipeline works end to end, verified against
live sources, not assumed — see below. Two of the three originally-planned sources turned
out not to hold up on direct verification; the plan was corrected in response, not papered
over.

## Phase 0 — Prove the data pipeline ✅ core pipeline done 2026-10-27

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

**Real open questions, not resolved yet**:
- Full-scale enrichment (all ~49,000 accepted taxa, not just 10) takes real time against the
  live API — the data package's own `metadata.yaml` estimates ~1.5 hours with 10 parallel
  threads. Needs a real rate-limiting/resumability plan before running at scale, not just
  looping the prototype script.
- Re-verify BRIT's NAEB site (may have been a transient connectivity issue, not confirmed
  dead).
- Pipeline-test Wikipedia's own toxicity content as the real poison-data source, the same
  way USDA PLANTS just got tested — not yet done, this was ruled promising but unverified.
- How a "red-alert" severity gets derived honestly once a real poison-data source is
  pipeline-tested, rather than invented.

## Phase 1 — Pick the real storage/app shape

Build it like WayStation (its own project, own repo — already true) — but WayStation itself
is a Tauri/Rust/React desktop app; whether Baneward matches that exact stack or picks
something lighter-weight while keeping the same "own standalone app, tied into Citadel
later" shape is a real decision not made yet. Needs: offline-first local storage for a
large (tens of thousands of entries) searchable dataset with images, a real search/filter
UI, and a real edit flow that enforces the unverified-until-confirmed rule from `README.md`.

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
