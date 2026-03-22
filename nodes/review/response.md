`★ Insight ─────────────────────────────────────`
**The CORS gap is the most instructive finding here.** The spec claims "all curl examples confirmed working" — but curl doesn't enforce CORS, browsers do. This is a classic verification gap: the tool used for testing doesn't exercise the same code path as the actual user. When documenting browser-facing APIs, always verify from a browser, not from curl.

**The "encrypted" claim reveals a spec-vs-implementation honesty problem.** The product spec (Layer 3) defines encryption as an architectural boundary. The docs inherited the word "encrypted" from the spec without checking whether milestone 1 implements it. This is how aspirational architecture silently becomes false documentation — the spec says what the system *should* be, the docs say what it *is*, and copy-paste bridges the gap dishonestly.

**Browser bypass of the event spine is the deepest architectural issue.** The docs describe the spine as "source of truth" but browser-initiated miner commands don't write to it. The architecture doc actually annotates this honestly with `[CLI path only]` in the flow diagram — but honesty buried in a flow diagram annotation doesn't protect the operator who reads "source of truth" in the prose and assumes completeness.
`─────────────────────────────────────────────────`

## Review Summary

**Conditional pass** with 3 blockers:

| # | Blocker | Why it matters |
|---|---------|----------------|
| **C1** | "Encrypted" claim is false | spine.py and architecture.md say "encrypted" — the code writes plaintext JSONL. Misleads operators about their security posture. |
| **C2** | No CORS headers in daemon.py | The documented quickstart (open index.html → fetch to :8080) will fail in modern browsers. curl verification doesn't catch this. |
| **C3** | README capability typo | Says "Control-only clients can monitor. Control-only can command." — should be "Observe-only" / "Control-capable". |

The deepest finding from the Nemesis passes is **N5**: browser-initiated control commands change miner state but don't write to the event spine, violating the "source of truth" claim. The docs are technically honest about this (the flow diagram annotates `[CLI path only]`) but don't flag it as a known limitation.

8 additional recommendations and 6 informational findings are in the full review at `outputs/documentation-and-onboarding/review.md`.