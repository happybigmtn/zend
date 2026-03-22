The polish pass is complete. Here's a summary of what was corrected and why:

## Changes Made

### `docs/api-reference.md`
- Removed 2 phantom HTTP endpoints (`GET /spine/events`, `POST /pairing/bootstrap`) — they are CLI-only, not in the daemon
- Changed all auth claims from "Control capability required" to **"Auth: None"** — daemon has no auth enforcement
- Added **Security Model** section at top explaining network isolation is the only access control
- Added **CLI-Only Commands** section with correct `python3 cli.py ...` syntax
- Added `ZEND_DAEMON_URL` to env var table
- Added note that `--kind` filter has a known crash bug (type mismatch in `cli.py:190`)
- Documented bootstrap non-idempotency

### `docs/architecture.md`
- Honest system overview: "no auth at the HTTP layer"
- Fixed component diagram: shows two distinct paths (CLI with auth+spine vs HTML gateway with neither)
- Auth model: daemon has no auth, CLI checks capabilities, token fields are dead code
- Data flow: shows both CLI and HTML gateway paths
- Known Limitations table: token fields unused, state world-readable, bootstrap non-idempotent, `--kind` crash, no file locking

### `docs/operator-quickstart.md`
- Security section rewritten: no auth exists, any LAN device can control, honest threat model
- Firewall setup corrected: ufw processes in order, note about deny rule placement
- Bootstrap non-idempotency added to Recovery section

### `README.md`
- Quickstart step 5 fixed: explicit `pair --capabilities observe,control` before first control command
- ASCII diagram rewritten with correct alignment and honest labels
- `ZEND_DAEMON_URL` added to Daemon Controls section
- Security note pointing to operator quickstart

### `outputs/documentation-and-onboarding/spec.md`
- Updated to reflect all corrections made in polish pass

### `outputs/documentation-and-onboarding/review.md`
- Rewritten as honest post-polish review: PASS verdict, all blocking issues addressed