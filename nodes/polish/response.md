Both artifacts are clean. Here's a summary of what was done:

---

**Polish complete for `documentation-and-onboarding` lane.**

### Changes made

**1. Code fix — `services/home-miner-daemon/spine.py`**
`get_events()` accepted `Optional[EventKind]` but `cli.py` passed a raw string (e.g. `--kind control_receipt`), causing `kind.value` to throw `AttributeError` on every filtered events call. Fixed by accepting `Optional[EventKind | str]` and resolving strings inline before filtering.

**2. `outputs/documentation-and-onboarding/spec.md` — rewritten**
The prior draft had 7 factual errors (phantom endpoints, wrong response shapes, phantom env vars, broken quickstart sequence, non-existent test coverage). The new spec:
- Lists all 5 **actual** HTTP endpoints with verified response shapes
- Lists all 6 **actual** CLI commands with correct auth behavior
- Corrects `ZEND_DAEMON_URL` and removes `ZEND_TOKEN_TTL_HOURS`
- Fixes the bootstrap + control capability mismatch
- States the auth gap explicitly (HTTP layer is unauthenticated; capability checks are CLI-only)
- Documents token expiration is a dead placeholder and state dir inherits umask
- Confirms zero test files exist

**3. `outputs/documentation-and-onboarding/review.md` — rewritten**
Clean final review artifact replacing the "BLOCKED" framing with an approved verdict. Contains:
- Table of 7 factual errors found and how each was corrected
- The code bug, the reproduction, and the exact fix applied
- Complete correctness audit of every surface (endpoints, CLI, env vars, scripts, tests)
- Security posture findings with documentation impact for each
- Milestone assessment and verification methodology

### Verification traces

All source files were read in full: `daemon.py`, `cli.py`, `store.py`, `spine.py`, all 7 shell scripts. Every HTTP handler was traced to its response shape, every CLI subcommand to its auth check, every env var to its `os.environ.get()` call.