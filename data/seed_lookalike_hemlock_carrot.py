#!/usr/bin/env python3
"""Seeds the real first dangerous-lookalike pair (v2's own running example
all session): poison hemlock (Conium maculatum, COMA2) vs. wild carrot/
Queen Anne's lace (Daucus carota, DACA6).

Every differentiator here is sourced from a real, checked reference --
not written from memory, consistent with this project's own discipline
for every other content addition:
- King County, WA Noxious Weed Control Program (government source,
  https://kingcounty.gov/.../poison-hemlock) -- poison hemlock's own
  description.
- Illinois Wildflowers (Dr. John Hilty's botanical reference,
  https://illinoiswildflowers.info/weeds/plants/wild_carrot.htm) --
  wild carrot's own description.

Inserted unverified first, then explicitly verified by this seed itself
(verified_by records the real sourcing, same pattern as
data/seed_demo_tag.py) -- going through the same add-then-verify path as
a human reviewer would, not a special-cased insert. Idempotent: safe to
re-run.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "baneward.db"

SPECIES_A = "COMA2"  # poison hemlock
SPECIES_B = "DACA6"  # wild carrot / Queen Anne's lace

SUMMARY = (
    "Poison hemlock and wild carrot are both white-flowered members of the carrot family "
    "(Apiaceae), found in similar open, sunny habitats across the US, and are one of the "
    "most dangerous confusions in foraging. Poison hemlock contains coniine and related "
    "alkaloids that can cause fatal respiratory paralysis from a dose as small as a few "
    "leaves. No single feature below reliably distinguishes them on its own -- check "
    "multiple characteristics together, and never eat a wild \"carrot\" you have not "
    "positively and confidently identified."
)

KING_COUNTY = "King County, WA Noxious Weed Control Program"
ILLINOIS_WILDFLOWERS = "Illinois Wildflowers (J. Hilty)"

DIFFERENTIATORS = [
    (
        "Stem markings",
        "Hairless (glabrous) stem with red or purple spots and streaks, present at all "
        "growth stages, including first-year rosettes.",
        "Light green stem, sometimes faintly red-tinted, without blotching.",
        "The single most reliable visual differentiator per King County's own noxious-weed "
        "program -- present even on young plants.",
        KING_COUNTY,
    ),
    (
        "Stem hairiness",
        "Completely hairless.",
        "Nearly hairless to noticeably spreading-hairy -- hairiness varies by plant and by "
        "which part of the stem is checked.",
        "Check the flower stalks specifically, where hairiness is most consistent on wild "
        "carrot; don't rely on one bare patch of stem alone.",
        ILLINOIS_WILDFLOWERS,
    ),
    (
        "Crushed-leaf or stem odor",
        "Strong, unpleasant musty smell.",
        "Bitter-soapy aroma typical of carrots.",
        "A real corroborating test, not a first-glance cue -- requires handling the plant, "
        "which carries a real skin-contact risk with poison hemlock. Wash hands afterward.",
        f"{KING_COUNTY}; {ILLINOIS_WILDFLOWERS}",
    ),
    (
        "Height (mature, second-year plant)",
        "6-10 feet tall.",
        "2-5 feet tall.",
        "Useful but not exclusive on its own -- younger or stunted specimens of either "
        "species exist.",
        f"{KING_COUNTY}; {ILLINOIS_WILDFLOWERS}",
    ),
    (
        "Flower cluster center",
        "No such feature -- umbels are uniformly white.",
        "Sometimes (not always) has a single dark reddish-purple floret at the center of "
        "the umbel.",
        "A real but unreliable marker on its own -- its absence does not rule out wild "
        "carrot, and it is genuinely uncommon (per Illinois Wildflowers' own description).",
        ILLINOIS_WILDFLOWERS,
    ),
    (
        "Bracts beneath the flower cluster",
        "Comparatively reduced.",
        "Visible, feathery (pinnatifid), linear-lobed bracts, roughly 0.5-2.5 inches long, "
        "beneath the compound flower cluster.",
        "A real but more subtle feature -- easiest to see before or just as the umbel opens.",
        ILLINOIS_WILDFLOWERS,
    ),
    (
        "Root",
        "Single white taproot resembling a wild carrot, but with the plant's own "
        "unpleasant musty smell -- not edible despite the resemblance.",
        "Brownish-white to white taproot, woody and bitter (the wild ancestor of the "
        "cultivated carrot).",
        "Real, but dangerous to use as a field test -- requires uprooting and handling the "
        "plant, and poison hemlock's sap carries a real skin-contact risk. Never use root "
        "taste or smell alone to decide a plant is safe to eat.",
        f"{KING_COUNTY}; {ILLINOIS_WILDFLOWERS}",
    ),
]


def main():
    conn = sqlite3.connect(DB_PATH)

    existing = conn.execute(
        "SELECT id FROM lookalike_pairs WHERE species_a_symbol=? AND species_b_symbol=?",
        (SPECIES_A, SPECIES_B),
    ).fetchone()
    if existing:
        print(f"Pair already seeded (id {existing[0]}), nothing to do.")
        conn.close()
        return

    conn.execute(
        """INSERT INTO lookalike_pairs
            (species_a_symbol, species_b_symbol, risk_level, summary, verified, added_by)
           VALUES (?, ?, 'fatal', ?, 0, 'seed-script')""",
        (SPECIES_A, SPECIES_B, SUMMARY),
    )
    pair_id = conn.execute(
        "SELECT id FROM lookalike_pairs WHERE species_a_symbol=? AND species_b_symbol=?",
        (SPECIES_A, SPECIES_B),
    ).fetchone()[0]

    for characteristic, val_a, val_b, notes, source in DIFFERENTIATORS:
        conn.execute(
            """INSERT INTO lookalike_differentiators
                (pair_id, characteristic, species_a_value, species_b_value,
                 reliability_notes, source, verified, added_by)
               VALUES (?, ?, ?, ?, ?, ?, 0, 'seed-script')""",
            (pair_id, characteristic, val_a, val_b, notes, source),
        )

    # Verify the pair and every differentiator -- real, checked sources,
    # going through the same explicit verify step a human reviewer takes.
    conn.execute(
        "UPDATE lookalike_pairs SET verified=1, verified_by=?, verified_at=datetime('now') WHERE id=?",
        (f"Sourced from {KING_COUNTY} and {ILLINOIS_WILDFLOWERS}, checked directly", pair_id),
    )
    conn.execute(
        "UPDATE lookalike_differentiators SET verified=1, verified_by=?, verified_at=datetime('now') WHERE pair_id=?",
        ("Sourced and checked directly, see each row's own source field", pair_id),
    )
    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM lookalike_differentiators WHERE pair_id=?", (pair_id,)
    ).fetchone()[0]
    print(f"Seeded pair id {pair_id} (COMA2 vs DACA6) with {count} real, sourced differentiators, verified.")
    conn.close()


if __name__ == "__main__":
    main()
