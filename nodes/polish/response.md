Done. Both durable artifacts are now polished and accurate:

**`outputs/hermes-adapter-implementation/spec.md`** — Updated to:
- Reference correct paths (`plans/2026-03-19-build-zend-home-command-center.md`, `references/hermes-adapter.md`)
- Remove references to non-existent `genesis/plans/` files
- Include accurate function table, endpoint matrix, and CLI command reference
- Document security model and test coverage (16 tests)

**`outputs/hermes-adapter-implementation/review.md`** — Updated to:
- Reference correct ExecPlan and contract files
- Include actual test names from `test_hermes.py`
- Add verification commands with expected outputs
- Document gaps vs future work from the contract
- Add progress checklist aligned to the ExecPlan

**Verification:**
- 16/16 tests pass ✓
- CLI `hermes` subcommands functional ✓
- All endpoint handlers wired correctly ✓