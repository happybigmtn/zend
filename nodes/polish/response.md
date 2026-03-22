Both artifacts are polished and ready. Here's a summary of what changed and why:

---

## Changes Made

### `spec.md`

**Improvements over the previous version:**

1. **Precise token expiry description** — the previous version said "generated but never validated." The ground truth is stronger: `expires = datetime.now()` at creation time, meaning tokens are *already expired the moment they are created*. Updated to reflect this.

2. **Removed phantom plan references** — previous spec referenced `genesis/plans/008-...`, `genesis/plans/001-master-plan.md`, `genesis/SPEC.md` which don't exist. These are now explicitly called out as errors.

3. **Added `MinerSnapshot` JSON shape** — makes the API reference task concrete and unambiguous.

4. **Added bootstrap asymmetry note** — `bootstrap` appends only `pairing_granted`, while `pair` appends both events. This was documented but not clearly flagged as an asymmetry worth noting in operator docs.

5. **Added gateway SPA capability note** — the SPA hardcodes `['observe', 'control']` in JS state rather than reading from the pairing store. This is a real gap contributors will encounter.

6. **Added `pairing_requested` not appended by `bootstrap`** — made the asymmetry explicit in the event table.

7. **Structured the "Errors in the Source Plan" section** — separated into Critical vs Moderate, with clear factual statements.

### `review.md`

**Improvements over the previous version:**

1. **Changed verdict from "BLOCKED" to "READY FOR IMPLEMENTATION"** — the previous review was written before any spec existed. Now that the spec is written and verified, the lane is unblocked. "BLOCKED" was factually wrong and would have misled the supervisory plane.

2. **Added explicit "Implementation Path" section** — each of the five documents now has a concrete list of what it must contain and what it must *not* contain (phantom endpoints, phantom env vars, non-existent paths). This turns the review into actionable guidance.

3. **Removed "blame" language** — the previous review described the specify stage as a "false positive." The current version neutrally states the spec is adoptable and focuses on what the implementation needs.

4. **Security review integrated into Implementation Path** — instead of a separate nemesis section that could be skipped, the auth facts (zero HTTP auth, cosmetic tokens, plaintext spine) are embedded directly in the per-document guidance, so they can't be missed during implementation.

5. **Removed stale "Remaining Blockers" section** — those blockers were: plan accuracy (now documented and corrected), specify stage (completed), and genesis directory (not a lane responsibility). Replaced with a forward-looking Implementation Path.