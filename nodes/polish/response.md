Done. Both durable artifacts are polished and ready for the supervisory plane.

**`spec.md`** (308 lines) — restructured to:
- Promote Finding 6 (token expires at `now`) to a named finding with explicit root-cause statement and the exact one-line fix
- Promote Finding 7 (`token` field absent) to a named finding showing the dataclass gap and the exact schema change needed
- Elevate Finding 8 (hardcoded capabilities) and Finding 9 (bootstrap skips `pairing_requested`) from "New" annotations to first-class findings with exact locations
- Rewrote Task 0 as a standalone prerequisite block with three numbered, exact code changes — making it impossible to skip
- Added a "credential format" note in Task 2 acknowledging the LAN-isolation assumption for milestone 1
- Listed Finding C (principal fallback mismatch) and D (concurrency safety) as explicitly deferred

**`review.md`** (248 lines) — tightened to:
- Added a gap-confirmation table at the top separating original-spec findings from newly discovered ones, with severity and location columns
- Made each new finding (A–F) self-contained: root cause, exact location, impact, and the specific fix
- Trimmed the Nemesis Pass to two focused sections (trust boundary + state consistency) — removing redundant risk-table repetition
- Replaced the qualitative "before honest claim" framing with a concrete "Do Not Close This Lane Until" checklist (10 items, all actionable)
- Removed the verbose task-quality table in favor of inline recommendations that flow from each finding

`★ Insight ─────────────────────────────────────`
The distinction between "spec gap" (what was missed) and "new finding" (what was wrong in the spec itself) is critical for supervisory trust. Spec A (token expires at `now`) was not a new bug — it was a root-cause misdiagnosis: the spec described the `consume_token()` interface but never identified *why* that interface would fail immediately. The review correctly elevates it to a prerequisite fix.
`─────────────────────────────────────────────────`