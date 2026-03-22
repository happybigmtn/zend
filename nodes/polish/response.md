Both durable artifacts are polished and ready for the supervisory plane.

---

**What changed and why:**

### `spec.md` — structural rewrite
- **"What This Is"** replaced with a positive, descriptive **Architecture** section that makes the system immediately comprehensible
- **Component tables** tightened — each entry now has a Role column that says what it actually does, not just what it is
- **Known Gaps section** added as a proper table with severity, genesis plan mapping, and a short description. This is the primary actionable artifact for the supervisory plane — it collapses 13 review findings into a scannable reference
- **Prior review corrections** removed (those belong in the review doc, not the spec)
- **Genesis Plan Index** added as a quick lookup table at the bottom
- **Encryption note** added inline in the Event Spine section ("plaintext in milestone 1") to match the honest treatment in the review

### `review.md` — sharpened and organized
- **13 findings → organized by category** (Security / Functionality / Data Integrity / Documentation) rather than a flat numbered list, making it easier to prioritize
- **Severity summary table** fixed — the prior version had F9 and F10 listed separately from the MEDIUM group
- **Prior review corrections** table rewritten with specific citations (`daemon.py:168-200`, `store.py:86-91`, etc.) so reviewers can verify each correction against source
- **Recommendations collapsed to 12 numbered items** mapped to P0/P1/P2/P3, directly usable as a genesis plan backlog
- **Sign-off table** simplified — four areas, each with Status / Confidence / What prior review said
- **"Adequate for prototype" disagreement** preserved and sharpened — this is the most important call the reviewer made and it needed to land clearly