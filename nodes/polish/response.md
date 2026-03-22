Done. Two durable artifacts written to `outputs/carried-forward-build-command-center/`:

**`spec.md`** (11.6 KB) — the authoritative specification for milestone 1:
- Declares what is and is not in scope, in plain language
- Defines all data types (`PrincipalId`, `GatewayCapability`, `MinerSnapshot`, `EventKind`)
- Specifies the daemon HTTP API with exact paths and methods
- Specifies the six CLI script interfaces with their exact argument signatures and expected outputs/errors
- Lists the seven required reference documents with their purposes
- Lists the 13 required automated tests by name and what each validates
- States the 10 acceptance criteria
- Explicitly supersedes the stale draft at `outputs/home-command-center/`

**`review.md`** (8.1 KB) — the honest review record:
- States the outcome as **FAIL — Deterministic** with the exact failure signature
- Explains that the prior "approved" verdict was aspirational — no implementation exists
- Documents the current repository state as planning-only with a table of what exists vs. what is missing
- Identifies the root cause: the verification commands have no target because `services/`, `scripts/`, and `upstream/manifest.lock.json` are all empty
- Maps the 8 open genesis-plan tasks to the 15 remaining ExecPlan checklist items
- Provides exact commands the supervisory plane should run on re-entry