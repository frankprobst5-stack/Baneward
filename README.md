# Baneward

**An offline, searchable, editable US wild plant database — edible, medicinal, and
poisonous — with images, red-alert warnings, and local-AI search help.**

Part of the [Citadel Ecosystem](https://github.com/frankprobst5-stack/citadel-ecosystem).
Built standalone, like [WayStation](https://github.com/frankprobst5-stack/WayStation), then
tied into [Citadel](https://github.com/frankprobst5-stack/Project-Citadel) once it's real.

## Why

A real, repeated ask: if the grid is down and nobody can look it up online, can you actually
tell whether what's in front of you is food, medicine, or something that'll hurt you?
Existing wild-edible apps and guides either don't work offline, aren't editable, or are
copyrighted content that can't legally be redistributed. Nothing checked so far (a real
GitHub search, 2026-10-26) comes close — this is original work, not a reuse candidate.

## The one rule everything else follows

**This is the one place in the whole ecosystem where being wrong has the highest real
cost.** Every design decision gets weighed against that first. Concretely:

- **Local AI help searches and explains already-sourced, verified entries. It never
  generates a new safety determination on its own.** A hallucinated "yes, safe to eat" is
  the single worst thing this project could ship. This matches Citadel's own Global
  Situation Monitor precedent — a real AI hallucination was caught in testing there, which
  is exactly why that feature ships with a human approve/reject queue before anything
  AI-suggested goes live.
- **New or edited entries default to unverified/no-claim until a human confirms them
  against sourced data.** A red-alert box is only trustworthy if nothing can go green by
  accident.
- **Data comes from real, authoritative, legally reusable sources — not scraped foraging
  blogs.** See below.
- **Absence of evidence is not evidence of safety. Identification confidence is not safety
  confidence.** A species with no documented poison claim must never render as "safe" —
  missing data means unreviewed, not clean. And a plant matching someone's described
  characteristics is a candidate to investigate further, never a confirmed identification
  to act on. These are two different kinds of uncertainty and neither one is allowed to
  quietly become certainty anywhere in the Rust layer, the schema, or the UI.

## Real data sources (researched 2026-10-27)

Three authoritative, cross-linked, legally clean sources instead of one invented database:

1. **[USDA PLANTS Database](https://plants.usda.gov)** — ~90,000 US species, full taxonomy
   and distribution, real bulk CSV download, public domain/CC0. 50,000+ images, each one
   flagged with its own copyright status on its plant profile page — only the
   public-domain-tagged subset is usable here, filtered at ingest, attribution kept
   regardless.
2. **USDA ARS International Checklist of Poisonous Plants** (via GRIN) — ~5,000 scientific
   names / ~12,000 common names documented as toxic to humans or animals. The real backbone
   for the poison/red-alert data — a government checklist, not an invented severity scheme.
3. **Native American Ethnobotany Database** (BRIT, 25 years of academic work) — 44,691 real
   documented entries of food/medicine/dye/fiber use by 291 Native American groups across
   4,029 species, about half medicinal, already cross-linked to USDA PLANTS by species. The
   real backbone for edible/medicinal classification.

Supplementary cross-reference sources: CDC NIOSH's poison ivy/oak/sumac guidance, USDA ARS's
own Poisonous Plant Research Laboratory (Logan, UT) publications, and poison.org (America's
Poison Centers) as a sanity check, not a bulk data source.

## Status

**A real, working app.** All 35,326 real US species from USDA PLANTS are ingested and
ship bundled inside the app itself — it runs standalone, with the data already there, the
same way [WayStation](https://github.com/frankprobst5-stack/WayStation) does. Search,
species detail, the unverified-by-default claims system, and now adding your own photo to
a species (same unverified-by-default rule) all work and are verified live. Not yet done:
Citadel integration, local AI search, and caching real image bytes instead of live USDA
URLs. See [ROADMAP.md](ROADMAP.md) for the real detail.

```bash
cd app
npm install
npm run tauri dev
```

## License

GPL-3.0-or-later, matching the rest of the Citadel Ecosystem.
