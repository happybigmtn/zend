Both artifacts are now polished. Here's a summary of the changes:

---

**`spec.md` — key revisions**

- **Grounded in reality:** Added an explicit "What Exists vs. What Is Planned" table showing all 7 scripts, all 6 reference documents, and all service files as present in the repo today.
- **Removed "encrypted" mischaracterization:** The spec now describes the spine as a plaintext JSONL append-only journal and the gap is explicitly listed under Known Gaps.
- **Security table:** Added an intent-vs-implementation comparison table so a supervisor can read at a glance which properties are documented vs. actually enforced.
- **Directory layout table:** Replaced generic descriptions with concrete, repo-relative paths and line-number hints where the review found issues.
- **Known Gaps section:** Consolidated the 12 findings from the review into a numbered, prioritized list that mirrors the review's blocker ordering.
- **Acceptance criteria:** Reworded as outcome-stated criteria that describe what the spec *requires*, not what the code currently does.

**`review.md` — key revisions**

- **Supervisory plane framing:** Added a header note that this review supersedes the prior premature approval, and a closing summary that gives a recommended next-action sequence for a human supervisor.
- **Tightened prose:** Removed redundant phrasing in Pass 1 findings (e.g., collapsed the two-paragraph daemon-auth finding into one precise statement with location, impact, and required fix).
- **Severity normalization:** All CRITICAL and HIGH findings are now consistently labeled with consistent language ("Required fix:" format for the action).
- **Gap analysis table:** Converted from prose to a compact three-column table (criterion / intent / implementation) for fast supervisory scanning.
- **Removed "Artifact Path Mismatch" section:** That was an internal correction note; it doesn't belong in the supervisory-plane review.
- **Consistent terminology:** "pass 1" / "pass 2" headings standardized; "Hermes adapter" consistently referenced as "contract only" where applicable.