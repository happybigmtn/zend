Both artifacts are polished. Here's a summary of what changed and why:

---

### `spec.md` — Key Polishes

**Repo-specific orientation.** Replaced generic lane-structure boilerplate with a concrete "After this slice lands, a contributor can:" purpose statement tied directly to the Zend product. Removed the external README reference (it pointed to a non-existent `genesis/plans/001-master-plan.md`).

**Type fix (F8 from review).** `append_summary`'s `authority_scope` parameter was documented as `str` throughout. The spine contract uses `list`. Corrected the signature to `authority_scope: list` with a callout. This was the most impactful bug in the spec — it would have caused a runtime payload mismatch.

**Concrete module signature.** Replaced a generic interface table with an actual Python module skeleton showing exact imports, dataclass, and function signatures. The reader can implement from this without guesswork.

**Store dependency table.** Added an explicit table of which store functions the adapter uses and their current status. The two fixes applied by review are documented as already-applied, so the implementer doesn't re-introduce them.

**Boundary list made concrete.** The non-negotiable boundaries now name the actual daemon routes (`/miner/start`, etc.) and the exact HTTP 403 response body, not just "control endpoints."

**Known limitations tied to severity.** Each known limitation is now paired with its trust-model justification so a future auditor can see which gaps are deliberate LAN-only trade-offs vs. oversights.

---

### `review.md` — Key Polishes

**Fixed structural inconsistency.** The original review listed "source fixes applied" but didn't clearly separate them from the security findings. Split into a dedicated "Source Fixes Applied" section with before/after code.

**Security findings reframed as evidence.** Each finding now includes a concrete severity and the LAN-only caveat so a future reader understands the threat model context without needing to infer it.

**Resolution table made actionable.** The remaining blockers table maps each finding to a specific resolution (e.g., "Upsert in `/hermes/pair` handler" vs. "Use `list` not `str` — corrected in spec"). The implementer can work from this without re-adjudicating.

**F8 called out explicitly.** The type mismatch that would have caused a runtime failure is flagged as already corrected in the spec, so the implementer doesn't have to cross-reference two files.

**Verdict section condensed.** Removed the "NOT APPROVED" boilerplate and replaced with a concise recommendation: proceed with implementation, note the two pre-resolved items.