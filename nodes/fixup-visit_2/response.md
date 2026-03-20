**Fixup complete.** Here's what was addressed:

## Changes Made

### 1. Created `outputs/hermes-adapter/integration.md` (was missing)
Documents:
- Integration points that exist (token storage, sibling module imports, HTTP API intention, spine integration intention)
- What's deferred (live daemon, real gateway, spine append)
- Package name note explaining the hyphenated directory requires `importlib.util` workaround

### 2. Fixed `outputs/hermes-adapter/verification.md`
- **Module Import Verification**: Removed incorrect `from hermes_adapter import ...` example that doesn't work with hyphenated package; documented that import verification is implicit via the test file's `importlib.util` pattern
- **Token Creation Test**: Removed broken inline script that used wrong import path (`hermes_adapter.token` instead of `hermes_adapter.auth_token`); replaced with reference to the test class that actually verifies this

## Verification
All 10 unit tests pass via `./scripts/bootstrap_hermes.sh`.

`★ Insight ─────────────────────────────────────`
The hyphenated package name (`services/hermes-adapter/`) is the root cause of the artifact mismatch. Python can't directly import from hyphenated directories — the test file uses `importlib.util.spec_from_file_location()` to work around this. The original verification.md incorrectly assumed `from hermes_adapter import ...` would work.
`─────────────────────────────────────────────────`

## Remaining State
The `promotion.md` still has `merge_ready: no` — that file is owned by the Settle stage and will be re-evaluated there. The fixup has resolved the artifact mismatches that caused the original rejection.