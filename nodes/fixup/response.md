The `integration.md` is created and `verification.md` is updated. However, `promotion.md` has `merge_ready: no` set by the settle stage, which I cannot modify per priorities.

`★ Insight ─────────────────────────────────────`
The settle stage ran with gpt-5.4 and produced `promotion.md` with `merge_ready: no` because it judged "contract mismatches in pairing and event outputs" existed at that time. The bootstrap now passes, but settle's judgment was based on its evaluation window. Fixup's job is to address integration.md (done) and refresh verification with the passing proof (done). The settle agent will re-evaluate on the next settle run.
`─────────────────────────────────────────────────`

The fixup is complete. Summary of changes:
- Created `outputs/private-control-plane/integration.md` documenting HTTP API surface, CLI scripts, state files, capability scopes, and lane dependencies
- Updated `verification.md` with fresh bootstrap proof showing exit 0

The audit will still fail on `merge_ready: no` in `promotion.md` — that file is owned by settle and cannot be rewritten during fixup. The pipeline will route back through verify → quality → settle after fixup completes, allowing settle to re-evaluate with the fresh evidence.