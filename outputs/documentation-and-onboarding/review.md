# Review — Documentation & Onboarding

**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-23
**Verdict:** In review — polish pass

## Summary

The documentation slice covers all required surfaces (README, contributor guide,
operator quickstart, API reference, architecture). Seven categories of incorrect
claims were identified. The fixes are surgical and do not require structural
changes. After correction the docs will be honest and executable from a fresh
clone.

---

## Findings

### Finding 1 — README quickstart control step uses observe-only device [HIGH]

**Location:** `README.md:31-33`

The quickstart bootstraps with `alice-phone` (observe-only by default) and then
immediately issues a `control` command with that same device name. The control
step fails with `unauthorized` because bootstrap only grants `["observe"]`.

**Fix required:** The quickstart must either:
- Pair a second device with `control` capability before the control step, or
- Use `bootstrap --device` with a name and then `pair --capabilities
  observe,control` for that same device before control, or
- Change the bootstrap device to have `control` by default

The simplest honest fix: add a `pair` step before the control step, using a
different device name:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control
```

Then the control step will succeed.

---

### Finding 2 — Gateway HTML hard-codes API base; phone flow won't reach home hardware [HIGH]

**Location:** `apps/zend-home-gateway/index.html:632-637` (API_BASE constant)

The operator quickstart (`docs/operator-quickstart.md:153-165`) says the phone's
browser will automatically poll the daemon at the home machine's LAN IP. The
actual UI is hard-coded to `http://127.0.0.1:8080`, which resolves to the
phone itself, not the daemon machine.

**Fix required:** The operator quickstart must be honest about this limitation.
For milestone 1 the correct workflow is:
1. Serve the HTML from the daemon machine (not the phone): `python3 -m http.server 9000`
2. Access the command center at `http://<daemon-lan-ip>:9000/index.html`
3. The served HTML still polls `http://127.0.0.1:8080` — which works because
   the browser is on the same machine as the daemon in this deployment model

Alternative: the docs should note that for the phone to be the browser client,
the daemon must be accessed from the phone over LAN, and the HTML must either
be served from the daemon machine or modified to use a configurable API base.

---

### Finding 3 — `/spine/events` documented as HTTP endpoint; does not exist [HIGH]

**Location:** `docs/api-reference.md:100-154`

The API reference presents `GET /spine/events` as a live HTTP endpoint with curl
examples. `daemon.py`'s `GatewayHandler.do_GET()` only serves `/health` and
`/status`; all other GETs return `404 not_found`. The review confirmed:
`curl /spine/events` → `404`.

**Fix required:** Remove the `GET /spine/events` section from the HTTP API
reference entirely. The event spine is accessible via CLI only:
`python3 cli.py events --client <name> [--kind <kind>] [--limit <n>]`. Document
the CLI command correctly (see also Finding 4).

---

### Finding 4 — `cli.py events --kind` crashes with `AttributeError` [HIGH]

**Location:** `services/home-miner-daemon/cli.py:190-191`

`cmd_events()` forwards `args.kind` (a raw string like `"control_receipt"`)
directly to `spine.get_events(kind=kind, ...)`. `get_events()` expects an
`EventKind` enum and calls `kind.value`, which raises `AttributeError: 'str'
object has no attribute 'value'`.

Runtime confirmation: `cli.py events --client my-phone --kind control_receipt
--limit 5` crashed with `AttributeError`.

**Fix required:** In `cmd_events()`, convert the string to `EventKind` before
calling `get_events()`. The architecture doc's spine section correctly shows
`get_events(kind: Optional[EventKind] = None, ...)`.

---

### Finding 5 — Token TTL and replay claims not implemented [MEDIUM]

**Locations:**
- `README.md:143-149`
- `docs/operator-quickstart.md:361-365`, `387-393`
- `services/home-miner-daemon/store.py:40-49`, `86-114`

The docs describe `ZEND_TOKEN_TTL_HOURS`, 24-hour token validity, single-use
tokens, and replay rejection. The implementation:
- Does not read `ZEND_TOKEN_TTL_HOURS` from the environment
- Sets `token_expires_at` to the current timestamp (not a future time)
- Never checks `token_used` or `token_expires_at` on use

**Fix required:** Remove these claims from docs, or mark them as deferred to
milestone 2. The environment variable table can keep `ZEND_TOKEN_TTL_HOURS`
with a note that it is not yet enforced.

---

### Finding 6 — Architecture doc misstates writer boundaries [MEDIUM]

**Location:** `docs/architecture.md:64-65`, `250-268`

The architecture doc says "the daemon is the only process that writes to the state
directory" and shows `spine.append_control_receipt()` happening inside the
daemon. In the current implementation the CLI writes principal state, pairing
state, and spine events directly through `store.py` and `spine.py`:
- `cli.py cmd_bootstrap()` → `spine.append_pairing_granted()`
- `cli.py cmd_pair()` → `spine.append_pairing_requested/granted()`
- `cli.py cmd_control()` → `spine.append_control_receipt()`

**Fix required:** Update the architecture doc to reflect that both the CLI and
the daemon write to the state directory. The daemon does not own the spine —
the CLI does. The daemon is the HTTP layer; the CLI is the state layer.

---

### Finding 7 — Minor correctness misses [LOW]

**specs/ path:** `README.md:121-123` and `docs/contributor-guide.md:205-206`
reference `specs/2026-03-19-zend-product-spec.md`, which does not exist in the
repo.

**Enum reprs:** `docs/api-reference.md:168-177` shows `/miner/set_mode` response
as `{"success": true, "mode": "balanced"}`. The daemon actually returns
`{"success": true, "mode": "MinerMode.BALANCED"}` (the enum repr). Similarly
`start` and `stop` return enum `status` values.

**Fix required:**
- Remove `specs/` path references or update to the correct path if the file is
  added later.
- Update API example responses to show enum reprs or update the daemon to return
  string values (the cleaner fix; the API contract should use strings, not Python
  enum reprs).

---

## Milestone Fit

| Requirement | Status |
|---|---|
| README quickstart complete end-to-end | ✗ — device lacks control capability |
| Operator quickstart works on home hardware | ✗ — hard-coded API base not addressed |
| API reference matches daemon surface | ✗ — `/spine/events` does not exist |
| Architecture doc reflects implementation | ✗ — writer boundaries wrong |
| Token/replay docs match code | ✗ — not implemented |
| Clean-machine verification possible | ✗ — `--kind` crashes |

---

## Action Plan

1. **[README]** Add `pair --capabilities observe,control` step for alice-phone
   before the control command in the quickstart.
2. **[operator-quickstart]** Rewrite phone/browse section to be honest about
   the hard-coded API base; document the served-HTML deployment model.
3. **[api-reference]** Remove `GET /spine/events` section; fix `set_mode`
   response example to show enum repr or update daemon to return strings.
4. **[cli.py]** Convert `args.kind` string to `EventKind` enum in `cmd_events()`.
5. **[docs — token/replay]** Remove TTL and replay claims; add "deferred to
   milestone 2" note if appropriate.
6. **[architecture.md]** Fix state-writer claims to reflect CLI writes state
   via `store.py`/`spine.py`.
7. **[all docs]** Remove `specs/2026-03-19-zend-product-spec.md` references.

---

## Verification Notes

```
./scripts/bootstrap_home_miner.sh          # succeeded
curl /health                              # {"healthy": true, ...}
cli.py status --client alice-phone        # worked
cli.py pair --device my-phone --capabilities observe,control  # worked
cli.py control --client my-phone --action set_mode --mode balanced  # worked
curl /spine/events                        # 404 not_found
cli.py events --kind control_receipt      # AttributeError crash
pytest services/home-miner-daemon/ -v     # 0 tests collected
```
