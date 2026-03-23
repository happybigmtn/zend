# Review — Documentation & Onboarding

**Lane:** `documentation-and-onboarding`  
**Date:** 2026-03-23  
**Verdict:** Blocked

## Findings

### 1. README quickstart is not executable as written

`README.md` tells the reader to bootstrap with `alice-phone` and then issue a
control command with that same device name, but bootstrap only grants
`["observe"]`. The control step therefore fails with `unauthorized`, so the
headline quickstart does not complete end to end.

- Docs: `README.md:31-33`
- Code: `services/home-miner-daemon/cli.py:73-79`
- Runtime check: fresh-state bootstrap succeeded; `cli.py control --client alice-phone ...`
  is not authorized afterward

### 2. The operator phone flow is broken by the gateway's hard-coded localhost API base

The operator guide says the phone-served command center will poll the miner at
the daemon machine's LAN IP automatically. The actual UI is hard-coded to
`http://127.0.0.1:8080`, which resolves to the phone itself, not the home
hardware, so the documented home-hardware browser flow cannot work as written.

- Docs: `docs/operator-quickstart.md:153-165`
- UI code: `apps/zend-home-gateway/index.html:632-637`

### 3. The API reference documents `GET /spine/events`, but the daemon does not expose it

`docs/api-reference.md` presents `/spine/events` as a live HTTP endpoint with
curl examples. `GatewayHandler.do_GET()` only serves `/health` and `/status`;
all other GETs return `404 not_found`. In clean-run verification,
`curl /spine/events` returned `404`.

- Docs: `docs/api-reference.md:100-154`
- Code: `services/home-miner-daemon/daemon.py:168-174`

### 4. Event filtering examples crash the CLI

The contributor guide and operator flows both encourage `cli.py events --kind`.
`cmd_events()` forwards a raw string into `spine.get_events()`, but
`get_events()` expects an `EventKind` and dereferences `.value`. The documented
filtering path therefore raises `AttributeError` instead of returning events.

- Docs: `docs/contributor-guide.md:158-163`
- Code: `services/home-miner-daemon/cli.py:190-191`
- Code: `services/home-miner-daemon/spine.py:82-87`
- Runtime check: `python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 5`
  crashed with `AttributeError: 'str' object has no attribute 'value'`

### 5. Token, TTL, and replay claims are not implemented

The docs describe `ZEND_TOKEN_TTL_HOURS`, 24-hour token validity, single-use
tokens, and replay rejection. The implementation does not read
`ZEND_TOKEN_TTL_HOURS`, does not persist any token value on `GatewayPairing`,
and sets `token_expires_at` to the current timestamp at creation time. Those
security claims are therefore speculative, not current behavior.

- Docs: `README.md:143-149`
- Docs: `docs/operator-quickstart.md:361-365`
- Docs: `docs/operator-quickstart.md:387-393`
- Code: `services/home-miner-daemon/store.py:40-49`
- Code: `services/home-miner-daemon/store.py:86-114`

### 6. The architecture document misstates who writes state and where spine appends happen

The architecture doc says the daemon is the only process that writes the state
directory and shows `spine.append_control_receipt()` happening inside the
daemon. In the current implementation, the CLI writes principal state, pairing
state, and spine events directly through `store.py` and `spine.py`. That makes
the document unreliable for onboarding new engineers.

- Docs: `docs/architecture.md:64-65`
- Docs: `docs/architecture.md:250-268`
- Code: `services/home-miner-daemon/cli.py:73-79`
- Code: `services/home-miner-daemon/cli.py:88-110`
- Code: `services/home-miner-daemon/cli.py:157-160`

### 7. Some documented repository structure and API examples are still inaccurate

Two smaller correctness misses remain:

- The docs describe a `specs/` directory and `2026-03-19-zend-product-spec.md`,
  but that path is not present in the repo.
- The API reference shows `/miner/*` responses using raw string enums, but the
  daemon currently serializes enum reprs such as `"MinerMode.BALANCED"` for
  `set_mode`, and similarly returns enum objects for `start` and `stop`.

- Docs: `README.md:121-123`
- Docs: `docs/contributor-guide.md:205-206`
- Docs: `docs/api-reference.md:168-177`
- Code: `services/home-miner-daemon/daemon.py:104`
- Code: `services/home-miner-daemon/daemon.py:113`
- Code: `services/home-miner-daemon/daemon.py:133`

## Milestone Fit

This slice does not yet satisfy the lane brief.

- README quickstart: not complete end to end
- Contributor guide: useful, but one documented command path crashes
- Operator quickstart: browser-on-phone path is blocked by the hard-coded API base
- API reference: does not match the real daemon surface
- Architecture doc: contains important implementation inaccuracies
- Clean-machine verification: cannot be honestly marked complete yet

## Verification Notes

Runtime checks performed in a throwaway clone:

- `./scripts/bootstrap_home_miner.sh` succeeded on a fresh state directory
- `curl /health` returned `{"healthy": true, ...}`
- `python3 services/home-miner-daemon/cli.py status --client alice-phone` worked
- `python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control` worked
- `python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced` worked
- `curl /spine/events` returned `404 not_found`
- `python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 5` crashed
- `python3 -m pytest services/home-miner-daemon/ -v` collected `0` tests

## Remaining Blockers

1. Fix the README quickstart so the documented device can actually perform the
   documented control action.
2. Make the command center choose the daemon host dynamically, or rewrite the
   operator guide to a truthful flow that works on home hardware.
3. Either implement `/spine/events` in the daemon or remove it from the HTTP
   API reference.
4. Fix `cli.py events --kind ...` to pass a valid `EventKind`.
5. Remove or implement the documented token TTL and replay semantics.
6. Correct the architecture document's state-writer and event-flow claims.

## Overall Assessment

The docs are a meaningful draft, but not an honest reviewed slice yet. The lane
should stay open until the blockers above are resolved and the docs are
re-verified from a fresh clone.
