Both artifacts are polished. Here's a summary of what changed and why:

---

**`spec.md` — restructured for supervisory-plane readability**

- Added a **File Inventory** table at the bottom mapping every changed file to its role and scope
- Converted the public function table to include return types and a "Required Capability" column
- Added a **Known Issue** callout for the `MinerStatus` enum serialization bug (pre-existing, not introduced by this lane) so it doesn't surface as a surprise during milestone 2
- Replaced the generic architecture diagram comment with a precise **Security note** calling out that JWT signatures are deferred to plan 006
- Added a **Security Boundaries** section explicitly listing what is and is not enforced in milestone 1 — prevents the supervisory plane from misreading the current posture
- **Acceptance Criteria** converted to a checklist table with status column so it can be verified and signed off

**`review.md` — sharpened into an honest, actionable document**

- Split into three passes (First-Principles / Coupled-State / Supplementary) to make the severity hierarchy clear
- Every finding now has a **Location**, **Impact**, and **Recommendation** — the supervisory plane can act without re-reading code
- **Inline fixes** (CLI dispatch bug, argparse conflict) are documented as first-class items, not footnotes — they're the reason the lane passes at all
- **Verdict** explicitly gates lane close on F1-HIGH + F2-MEDIUM items rather than leaving it implied
- Pre-existing issues (enum serialization) are clearly separated so they don't look like lane regressions