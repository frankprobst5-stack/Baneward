# Baneward — Roadmap

Real, dated, honest about what's done vs. planned — same discipline every other project in
the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem) uses.

## Where things stand (2026-10-27)

Repo created, name chosen (`Baneward` — "bane" = poison, as in wolfsbane/henbane, + "ward" =
guard/protect, naming the core red-alert-for-poison feature directly), real data sources
researched and documented in `README.md`. No code written yet.

## Phase 0 — Prove the data pipeline

Before any UI: pull a real sample from each of the three sources (USDA PLANTS, USDA ARS's
Poisonous Plants Checklist, the Native American Ethnobotany Database), confirm they actually
cross-link by scientific name the way the research says they do, and confirm the
public-domain image filtering on USDA's gallery actually works against real plant profile
pages — not assumed from the README's own research, verified against the real sources
directly, same discipline as every other data-sourcing decision in this ecosystem.

Real open questions to resolve here, not guessed at now:
- Exact bulk-download mechanics for each source (USDA PLANTS has a real CSV download; the
  ARS Poisonous Plants Checklist and BRIT's Ethnobotany Database need their own real access
  methods confirmed, not assumed to be as simple).
- How species get matched across all three sources reliably (scientific name alone can be
  ambiguous across taxonomic revisions — needs a real, tested matching strategy).
- How a "red-alert" severity gets derived honestly from the ARS checklist's own real data,
  rather than invented.

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
