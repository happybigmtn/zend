Both artifacts are polished:

**`outputs/hermes-adapter-implementation/spec.md`** — Corrected to:
- Match actual module path `services/home-miner-daemon/hermes.py`
- Use accurate pipe-separated token format (`hermes_id|capabilities|expires_iso`)
- Remove non-existent plan file references
- Include precise CLI subcommand table
- List actual dependencies (spine, store, daemon)

**`outputs/hermes-adapter-implementation/review.md`** — Corrected to:
- Remove reference to non-existent `genesis/plans/009-hermes-adapter-implementation.md`
- Add explicit control blocking proof via `curl`
- Add table of design decisions with rationales
- Mark frontend as correctly deferred (not in scope)
- Include over-fetch pattern detail for event filtering
- Evidence sections reference actual CLI commands from `cli.py`