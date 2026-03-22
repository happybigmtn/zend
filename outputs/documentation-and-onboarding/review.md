# Documentation & Onboarding - Review

Status: Blocked — 3 issues must be fixed before lane can pass

Date: 2026-03-22
Reviewer: Nemesis pass (correctness + security)

## Verdict

The documentation lane produced 5 well-structured documents that cover the right topics. The architecture doc and contributor guide are accurate. However, the API reference and README quickstart contain factual errors — they document endpoints and workflows that do not exist in the current code. The original review claimed "all endpoints verified" which is false.

**Lane cannot pass until the 3 blocking issues are resolved.**

## Blocking Issues

### B1: Two documented API endpoints don't exist

**Severity**: Critical — documentation claims verifiability that cannot be reproduced

**Evidence**:
- `docs/api-reference.md:239-335` documents `GET /spine/events` and `GET /metrics` with curl examples
- `daemon.py:168-174` — `do_GET` only handles `/health` and `/status`, returns 404 for all other paths
- Events are read by the CLI directly from `state/event-spine.jsonl` via `spine.py`, never via HTTP

**Fix options** (pick one):
1. Remove `/spine/events` and `/metrics` from the API reference; document them as CLI-only operations
2. Implement the endpoints in `daemon.py` to match the documentation

**Recommendation**: Option 1. The plan's endpoint list included these from the spec, but the implementation chose CLI-only access for events. Document what exists, not what was planned.

### B2: README quickstart fails on steps 4-5

**Severity**: Critical — the "10 minutes to working system" promise breaks immediately

**Evidence**:
- `scripts/bootstrap_home_miner.sh` calls `cli.py bootstrap --device alice-phone` with `["observe"]` capability
- README steps 4-5 use `--client my-phone` — a device that was never paired
- Even if you substitute `alice-phone`, it lacks `control` capability, so step 5 (`control --action set_mode`) returns unauthorized

**Fix**: Add a pairing step to the quickstart between steps 2 and 3:
```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### B3: `events --kind` filter crashes at runtime

**Severity**: Moderate — documented CLI feature is broken

**Evidence**:
- `cli.py:191` passes a raw string (e.g., `"control_receipt"`) to `spine.get_events(kind=kind)`
- `spine.py:87` does `e.kind == kind.value` — calling `.value` on a `str` raises `AttributeError`
- The `get_events` type hint says `Optional[EventKind]` but the CLI passes a plain string

**Fix**: In `spine.py:87`, change `kind.value` to `kind` (since `e.kind` is already a string), or convert the CLI's string to `EventKind` before passing.

## Non-Blocking Issues

### N1: Operator quickstart claims LAN URL serves HTML

`docs/operator-quickstart.md:92` suggests accessing `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`. The daemon has no static file serving — this returns 404. The HTML must be opened via `file://` path or served by a separate web server.

**Fix**: Remove the HTTP URL from the LAN access section. Document that the command center is a local file opened in the browser, not served by the daemon.

### N2: `pkill -f "daemon.py"` is overly broad

`bootstrap_home_miner.sh:66` kills any process matching "daemon.py" system-wide, not just Zend's daemon. On a machine running other Python services, this could kill unrelated processes.

**Fix**: Use a more specific pattern: `pkill -f "home-miner-daemon/daemon.py"` or check the PID file only.

### N3: No `unpair` command

`store.py:101` raises `ValueError` on duplicate device names. Recovery requires deleting `pairing-store.json`. An `unpair` CLI command would be cleaner but is not required for this milestone.

### N4: Previous review claimed false verification

The original `review.md` stated "All curl examples verified against running daemon" and "All endpoints verified" while omitting `/spine/events` and `/metrics` from the verification table. This is not a code issue but a process issue — the specify stage produced claims without running the code.

## Security Review (Nemesis Pass)

### Trust boundaries

- **HTTP layer has no auth**: All endpoints are unauthenticated. Any process on the network can start/stop mining. The CLI is the only capability gate, but direct HTTP calls bypass it entirely. This is documented as a milestone 1 limitation in `docs/architecture.md:241` — acceptable for LAN-only scope.

- **`0.0.0.0` binding warning is correct**: `docs/operator-quickstart.md:237` correctly warns against binding to all interfaces. Good.

### Capability scoping

- **Bootstrap grants observe-only**: `cli.py:78` correctly limits the default pairing to observe. Control requires explicit pairing. This is the right default.

- **No capability revocation implemented**: `EventKind.CAPABILITY_REVOKED` exists in spine.py but no code path produces it. Architecture doc correctly notes this is future work.

### State safety

- **JSONL appends are not atomic**: `spine.py:64` opens file in append mode and writes a single line. On most filesystems, appends under ~4KB are atomic, but this is not guaranteed. A crash mid-write could leave a partial line. `_load_events` at line 57 would crash on `json.loads()` of a partial line. The architecture doc claims "skip corrupted lines" but the code doesn't implement this — it would raise `json.JSONDecodeError`.

- **Pairing store uses full file rewrite**: `store.py:82-83` rewrites the entire pairing file on every change. A crash during write loses all pairings. This is acceptable for milestone 1 with the documented `rm -rf state/*` recovery path.

- **PID file is not locked**: `bootstrap_home_miner.sh:96` writes PID without file locking. Two concurrent bootstrap runs could race. Low risk for home hardware use.

### Idempotence

- **Bootstrap is not idempotent**: Running bootstrap twice creates `alice-phone`, then fails on the second run because `pair_client` raises on duplicate device names. The script calls `stop_daemon` first which clears the process but not the state. The operator quickstart's recovery section correctly documents `rm -rf state/*` as the reset path.

## Artifacts Produced

| File | Lines | Accuracy |
|------|-------|----------|
| `README.md` | 109 | Quickstart broken (B2) |
| `docs/contributor-guide.md` | 272 | Accurate |
| `docs/operator-quickstart.md` | 319 | LAN URL wrong (N1) |
| `docs/api-reference.md` | 441 | 2 phantom endpoints (B1), kind filter broken (B3) |
| `docs/architecture.md` | 449 | Accurate |

## Recommendation

Fix B1, B2, B3 (small, targeted changes), then the lane passes. The documentation structure and coverage are good — the issue is purely factual accuracy in the API reference and quickstart flow.

Estimated fix effort: ~30 minutes of code changes.
