# Stabilize Failed Lanes — Review

Date: 2026-03-22
Reviewer: Claude Opus 4.6
Lane: stabilize-failed-lanes
Stage reviewed: specify (failed), plus full codebase audit of existing implementation

---

## 1. Lane Outcome Summary

The `stabilize-failed-lanes` lane failed at the `specify` stage with a
deterministic error. The Fabro CLI agent exhausted its output budget or hit a
handler serialization error before producing a well-formed spec artifact. The
failure signature shows truncated JSON containing token-usage metadata, not a
code error.

**Consequence:** The four target lanes were never investigated. No root-cause
analysis, no fixes, and no re-runs occurred. The spec and review artifacts were
never produced by the lane itself.

This review was produced by direct codebase audit, not by reviewing lane output.

---

## 2. Correctness

### 2.1 What works

The existing milestone-1 scaffold is structurally sound in its broad strokes:

- The daemon (`services/home-miner-daemon/daemon.py`) runs, binds to 127.0.0.1,
  and serves status/health/control endpoints.
- The CLI (`cli.py`) correctly gates control commands behind capability checks.
- The event spine (`spine.py`) implements append-only JSONL with typed event
  kinds matching the contract.
- The pairing store (`store.py`) creates principals and pairing records with
  UUIDs and timestamps.
- The mobile client (`apps/zend-home-gateway/index.html`) renders the four
  destinations (Home, Inbox, Agent, Device) with the correct design tokens.
- The reference contracts are complete and internally consistent.
- Shell scripts implement the expected interfaces from the ExecPlan.

### 2.2 What is broken

**B1. Pairing tokens expire at birth.**
`store.py:89` — `create_pairing_token()` sets `expires` to
`datetime.now(timezone.utc).isoformat()`, which is the instant of creation. Any
token validation that checks expiration will reject every token. This is a
correctness bug that blocks lane 3 (bootstrap) and any future token-validation
work.

**B2. Bootstrap is not idempotent.**
`cli.py:78` calls `pair_client(args.device, ['observe'])` which raises
`ValueError` if the device name already exists (`store.py:101`). The bootstrap
script catches exit codes but does not handle this case gracefully. Re-running
bootstrap fails instead of being safe to repeat.

**B3. `cmd_status` authorization is incomplete.**
`cli.py:47-48` checks `has_capability(args.client, 'observe') or
has_capability(args.client, 'control')`, but `args.client` is optional
(`add_argument('--client', help=...)`). When `--client` is omitted,
`args.client` is `None`, `has_capability(None, 'observe')` returns `False`
(because `get_pairing_by_device(None)` returns `None`), but the `if
args.client` guard on line 47 skips the check entirely. So omitting `--client`
bypasses authorization. This is also true for `cmd_events` (line 181).

**B4. `cmd_control` ignores `get_pairing_by_device` returning None.**
`cli.py:143` calls `get_pairing_by_device(args.client)` and assigns the result
to `pairing`, but never checks if `pairing is None`. If the client device does
not exist in the pairing store, `pairing` is `None` but the function proceeds to
make the daemon call anyway. The capability check on line 134 would catch this
(unpaired device has no capabilities), but the code path after the check is
still structurally unsound.

**B5. Event spine get_events filtering is broken for string arguments.**
`spine.py:82` — `get_events(kind=...)` accepts `Optional[EventKind]` but the
CLI passes a plain string from `args.kind`. `e.kind == kind.value` will fail
with `AttributeError` because a `str` has no `.value` attribute. The only reason
this hasn't surfaced is that `cli.py:190` maps `'all'` to `None`, and the user
would need to pass an exact `EventKind` enum member otherwise.

### 2.3 What is missing

**M1. No HTTP-layer authentication.**
The daemon has zero authentication. No header check, no token validation, no
pairing credential. Any process on the loopback or LAN can `curl
http://127.0.0.1:8080/miner/start` and start the miner. The entire capability
model in `store.py` is enforcement theater — it exists only in the CLI code
path, which the daemon HTTP layer does not call.

**M2. No Hermes adapter implementation.**
`references/hermes-adapter.md` defines a `HermesAdapter` interface, but no
corresponding code exists. The smoke test (`hermes_summary_smoke.sh`) calls
`append_hermes_summary` directly via Python imports with no authority check,
no adapter, and no capability scoping.

**M3. No control command serialization.**
The plan explicitly requires serialized control commands. The daemon uses
`threading.Lock` per-method (`MinerSimulator._lock`), but two concurrent HTTP
requests to different endpoints (e.g., `/miner/start` and `/miner/set_mode`)
can both acquire the lock sequentially and both succeed. There is no command
queue, no conflict detection, and no `ControlCommandConflict` error raised
anywhere.

**M4. No encryption on the event spine.**
The spec, the product spec, and the event-spine contract all describe the spine
as an "encrypted event journal." The implementation writes plaintext JSON to a
JSONL file on disk. No encryption, no key derivation, no memo transport
integration.

**M5. No automated tests.**
The plan requires tests for: replayed tokens, expired tokens, duplicate client
names, stale snapshots, conflicting control commands, daemon restart recovery,
trust-ceremony state transitions, Hermes adapter boundaries, event-spine
routing, audit false positives/negatives, empty inbox states, and
screen-reader announcements. Zero tests exist.

**M6. No `upstream/manifest.lock.json`.**
The fetch script `scripts/fetch_upstreams.sh` expects this file, but it does
not exist in the repository. Running the script fails immediately.

**M7. No gateway proof transcripts.**
`references/gateway-proof.md` does not exist. The plan requires it.

---

## 3. Milestone Fit

### Alignment with ExecPlan

| ExecPlan requirement | Status |
|---|---|
| Repo scaffolding (apps/, services/, scripts/, references/) | Done |
| Upstream manifest and fetch script | Script exists, manifest missing |
| Home-miner daemon with simulator | Done (bugs noted above) |
| Bootstrap script | Done (not idempotent) |
| Pair script | Done |
| Read status script | Done |
| Set mode script | Done |
| Hermes summary smoke | Exists but bypasses adapter |
| No-local-hashing audit | Done |
| Mobile-shaped client | Done (no auth integration) |
| PrincipalId contract | Done in references and code |
| Event spine contract | Done in references and code (no encryption) |
| Hermes adapter contract | Reference only, no implementation |
| Error taxonomy | Reference only, no code raises these errors |
| Observability events | Not implemented |
| Automated tests | None |
| Gateway proof transcripts | Missing |

### Verdict

The scaffold is approximately 50% of milestone 1. The daemon, CLI, scripts,
client, and reference contracts form a working skeleton. But the skeleton lacks
the security model, the Hermes adapter, the test suite, and the encryption
layer that the spec and plan require. The four lane failures are symptoms of
these structural gaps.

---

## 4. Remaining Blockers

### Critical (blocks all four lanes)

1. **HTTP authentication.** Until the daemon enforces credentials, the client
   lane stalls, the control-plane lane has false-positive port checks, and any
   automated test of authorization is meaningless.

2. **Token expiration bug.** Every pairing token is born expired. Fixing this
   is a one-line change (`store.py:89`) but it gates bootstrap and pairing
   flows.

### High (blocks specific lanes)

3. **Missing Hermes adapter** — blocks lane 2.
4. **Bootstrap idempotence** — blocks lane 3.
5. **Port conflict detection** — blocks lane 4.
6. **Missing `upstream/manifest.lock.json`** — blocks any lane that needs
   upstream dependencies.

### Medium (blocks completion but not re-run)

7. **No tests** — blocks validation and acceptance.
8. **No encryption** — the gap between spec and code must be documented even
   if encryption is deferred.
9. **No observability events** — structured log contract exists but code emits
   nothing.

---

## 5. Nemesis-Style Security Review

### Pass 1 — First-Principles Trust Boundary Challenge

**Q: Who can trigger the slice's dangerous actions?**

The daemon's dangerous actions are: start mining, stop mining, change mode.
These are exposed via unauthenticated HTTP POST on `127.0.0.1:8080`. Any
process on the host can trigger them. If `ZEND_BIND_HOST` is changed to a LAN
address (as the plan envisions for real deployment), any device on the LAN can
trigger them.

**Q: What are the trust boundaries?**

There are three intended trust boundaries, but only one is enforced:

| Boundary | Intended | Enforced |
|---|---|---|
| HTTP socket (daemon) | Pairing credential required | No — open to all |
| CLI layer (cli.py) | Capability check before daemon call | Yes — checks store |
| Hermes adapter | Authority token with scoped capabilities | No — adapter doesn't exist |

The CLI enforces capabilities, but the daemon is the actual network surface.
Capabilities checked at the CLI layer are like a lock on an interior door when
the front door is wide open.

**Q: Who can trigger pairing?**

Anyone who can call `cli.py pair --device <name>` with write access to the
state directory. There is no authorization required to create a new pairing
with `control` capability. The plan says pairing requires a trust ceremony,
but the code creates a pairing record with any requested capabilities
immediately.

**Q: Can an observer escalate to controller?**

Yes, trivially. The pairing flow does not require an existing controller to
approve a new pairing. Any call to `pair_client(name, ['control'])` grants
control. Alternatively, skip the CLI entirely and POST to the daemon HTTP API,
which has no capability checks.

**Q: Can Hermes exceed its authority?**

The adapter boundary does not exist in code. The smoke test demonstrates that
Hermes (or anything claiming to be Hermes) can call any spine function directly.
In milestone 1 Hermes should be limited to `observe` + `summarize`, but nothing
enforces this.

### Pass 2 — Coupled-State Review

**Paired state surfaces:**

1. **Pairing store ↔ Daemon state.** The pairing store (`state/pairing-store.json`)
   and the daemon's in-memory `MinerSimulator` are decoupled. The daemon has no
   knowledge of pairings. The CLI bridges them, but the HTTP layer does not.
   Mutation path: any HTTP client can mutate daemon state without a corresponding
   pairing record update.

2. **Principal store ↔ Event spine.** Events carry a `principal_id`, and the
   principal store creates the ID. These are consistent because the CLI always
   calls `load_or_create_principal()` before appending. But direct Python imports
   (as the Hermes smoke test does) can use any principal ID — there is no
   validation that the principal exists.

3. **Pairing store ↔ Event spine.** Pairing events are appended to the spine
   after the pairing record is created. If the spine append fails (file system
   error, permissions), the pairing record exists but the event does not. There
   is no transaction or rollback. This violates the contract that the event spine
   is the source of truth — the pairing store becomes an orphan source of truth.

4. **Client state ↔ Server state.** The HTML client stores `capabilities`,
   `principalId`, and `deviceName` in JavaScript memory and `localStorage`. These
   are never synchronized with the server. If the server revokes a capability,
   the client still shows the old permissions until page reload.

**Idempotence:**

- `bootstrap_home_miner.sh`: NOT idempotent. Second run fails on duplicate
  device name.
- `pair_gateway_client.sh`: NOT idempotent. Duplicate device raises ValueError.
- `fetch_upstreams.sh`: Idempotent by design (checks existing dirs).
- `no_local_hashing_audit.sh`: Idempotent (read-only).
- Event spine append: Idempotent in the sense that duplicate appends don't
  corrupt, but there is no deduplication — the same logical event can be
  appended multiple times with different UUIDs.

### Secret Handling

- No secrets exist in the codebase (no API keys, no private keys). This is
  appropriate for milestone 1 with a simulator.
- The pairing token is a UUID stored in plaintext JSON. It is not a
  cryptographic credential. This is acceptable for milestone 1 LAN-only, but
  must not carry forward to remote access.
- `PrincipalId` is a UUID with no associated key material. It is an identifier,
  not an authentication credential. Any code that treats it as proof of identity
  (rather than just a reference) is vulnerable to impersonation.

### Privilege Escalation Paths

1. **LAN peer → full miner control.** No authentication on daemon HTTP API.
   Severity: HIGH for any deployment beyond localhost.

2. **Observer → controller.** Call `cli.py pair --device new-name
   --capabilities observe,control`. No approval required. Severity: MEDIUM.

3. **Any Python import → spine write.** Direct `from spine import
   append_event` bypasses all checks. Severity: MEDIUM (requires code
   execution on host).

4. **Hermes → unrestricted spine access.** No adapter boundary. Severity:
   MEDIUM (same as above, demonstrated by smoke test).

### Service Lifecycle Safety

- `bootstrap_home_miner.sh` uses `kill -9` after `kill` with a 1-second sleep.
  This is aggressive but acceptable for a dev script.
- The PID file check (`kill -0 "$PID"`) is a standard TOCTOU race — the process
  could exit between the check and the subsequent action. Acceptable for
  milestone 1 dev tooling.
- `ThreadedHTTPServer` with `allow_reuse_address = True` means a new daemon can
  bind even if a previous one left the socket in TIME_WAIT. This is standard
  for dev servers but masks port conflicts in production.
- The daemon has no graceful shutdown beyond `KeyboardInterrupt`. There is no
  signal handler, no state flush, and no event-spine sync on exit. An
  in-progress control command could be lost.

---

## 6. Recommendations

### Immediate (unblock lane re-runs)

1. Fix `store.py:89` — token expiration must be in the future.
2. Make `cmd_bootstrap` idempotent — skip pairing if device already exists.
3. Add port-conflict detection in `daemon.py` before binding.
4. Create `upstream/manifest.lock.json` with at least a placeholder structure.

### Short-term (complete milestone 1)

5. Add minimal HTTP authentication: daemon checks `Authorization: Bearer
   <pairing_token>` header on all non-health endpoints.
6. Implement `HermesAdapter` class with authority-token validation.
7. Add at least one test per error class in the taxonomy.
8. Document that "encrypted" event spine is aspirational in milestone 1.

### Structural (prevent regression)

9. Move capability enforcement from CLI into daemon middleware so the HTTP
   layer is the single enforcement point.
10. Add transaction semantics or at least compensation logic for paired
    pairing-store + spine-append operations.

---

## 7. Verdict

**The lane is not shippable.** The `specify` stage failed at the meta level
(Fabro orchestration), and the underlying code has five correctness bugs, six
missing features, and a fundamental authentication gap.

The scaffold is real and worth preserving. The path forward is:

1. Fix the four specific root causes identified in the spec.
2. Add HTTP-layer authentication (the single highest-leverage change).
3. Re-run the four lanes against the fixed codebase.
4. Accept milestone 1 only after at least one automated test per error class
   passes.
