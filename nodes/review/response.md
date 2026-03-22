`★ Insight ─────────────────────────────────────`
**Python `(str, Enum)` serialization is a silent trap.** On Python 3.11+, `json.dumps()` of a `str, Enum` member produces the class-qualified name (`"MinerStatus.STOPPED"`) not the value (`"stopped"`). This changed from 3.10 behavior. The fix is explicit `.value` access. Alternatively, use `StrEnum` (3.11+) with a custom `JSONEncoder`, or always call `.value` at serialization boundaries. This is exactly the kind of bug that passes in dev (where you might read the output casually) but breaks machine consumers (UI code doing `=== 'stopped'`).

**Documentation reviews should verify claims against code, not trust author assertions.** The original self-review marked all 18 checklist items as "Verified" and downgraded the enum bug to "cosmetic." A 30-second Python one-liner proved the UI is broken. Reviews that don't run the code can't use the word "verified."
`─────────────────────────────────────────────────`

## Review summary

**Conditional Pass.** All five documentation deliverables are structurally complete, well-scoped to milestone 1, and cover the required sections. Two corrections were made to touched surfaces:

- `docs/architecture.md` — removed false claim that token expiry is validated
- `docs/api-reference.md` — clarified that HTTP endpoints are unauthenticated (capability checks are CLI-only)

### Two blockers remain (outside this lane, in daemon code):

| ID | File | Issue | Impact |
|----|------|-------|--------|
| **B1** | `daemon.py` | `json.dumps()` of `(str, Enum)` values produces `"MinerStatus.STOPPED"` not `"stopped"` | All API docs show wrong response format; gateway UI comparisons broken |
| **B2** | `cli.py` | `cmd_events` passes raw string to `spine.get_events(kind=...)` which calls `kind.value` | `--kind` filtering crashes with `AttributeError` |

Both fixes are ~1 line each. Until B1 is fixed, acceptance criteria #1 and #4 cannot be met. The documentation itself correctly describes the *intended* behavior — the code is what's wrong.

### Nemesis findings (no action needed for M1):

- HTTP endpoints have zero auth — by design, documented now
- Pairing tokens expire immediately and are never validated — documented now
- In-memory miner state resets on restart while spine retains old receipts — acceptable for simulator