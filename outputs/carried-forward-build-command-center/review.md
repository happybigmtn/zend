# Carried Forward: Build the Zend Home Command Center — Review

**Verdict:** REJECTED — Critical security gaps and spec divergence
**Lane:** carried-forward-build-command-center
**Reviewed:** 2026-03-22
**Prior Review:** outputs/home-command-center/review.md (APPROVED — overridden)

## Review Methodology

Two-pass Nemesis-style security review:

- Pass 1: First-principles challenge of trust boundaries, authority assumptions,
  and who can trigger dangerous actions
- Pass 2: Coupled-state review of paired protocol surfaces, mutation consistency,
  and failure modes

Additional checks: state transitions, secret handling, capability scoping,
privilege escalation paths, external process control, operator safety, idempotent
retries, and service lifecycle failure modes.

## Why the Prior Review Verdict Is Wrong

The prior review at `outputs/home-command-center/review.md` says "APPROVED —
First slice is complete." It acknowledges risks (unverified daemon, plaintext
events, no persistence, Hermes not connected) but still approves. This is
incorrect because the risks identified are not deferred polish — they are
violations of the spec's own invariants:

- "A paired client without `control` must not be able to change miner state"
  is violated (capability checks are client-side only)
- "the daemon must bind only to a private local interface" is unverified
  (0.0.0.0 is accepted via env var)
- "pairing must feel safe, named, and revocable" is violated (tokens are
  never checked)
- "encrypted event journal" is violated (plaintext JSON)

These are not gaps to fix later; they are the core trust promises of the product.

---

## Pass 1 — First-Principles Trust Boundary Challenge

### CRITICAL-1: No authentication on daemon HTTP surface

Location: `services/home-miner-daemon/daemon.py:168-200`

Every endpoint (`/status`, `/health`, `/miner/start`, `/miner/stop`,
`/miner/set_mode`) accepts requests from any caller with zero authentication.
The capability model (`observe` vs `control`) exists only in `cli.py` and the
shell scripts — it is enforced client-side, not server-side.

The gateway client HTML (`apps/zend-home-gateway/index.html:711,738,759`) does
JavaScript capability checks (`state.capabilities.includes('control')`) which
are trivially bypassed by calling the daemon API directly.

Impact: Any process on localhost can control the miner regardless of pairing
status or granted capabilities. The `observe`-only permission boundary is
fictional.

Spec violation: "A paired client without `control` must not be able to change
miner state."

### CRITICAL-2: LAN-only binding is not enforced

Location: `services/home-miner-daemon/daemon.py:34`

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
```

No validation ensures the bind address is private. Setting
`ZEND_BIND_HOST=0.0.0.0` exposes the unauthenticated daemon to the network.
The bootstrap script (`scripts/bootstrap_home_miner.sh:22`) also passes through
this env var without validation.

Plan violation: "Binding to `0.0.0.0` is not acceptable for milestone 1."

Fix: Validate against an allowlist of private addresses (127.0.0.0/8,
10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) and reject anything else.

### CRITICAL-3: Pairing tokens generated but never verified

Location: `services/home-miner-daemon/store.py:86-89`

```python
def create_pairing_token() -> tuple[str, str]:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc).isoformat()  # immediate expiration
    return token, expires
```

The token expires at creation time. `GatewayPairing.token_used` is initialized
to `False` but never set to `True`. No code path checks token validity,
expiration, or replay. The error taxonomy defines `PairingTokenExpired` and
`PairingTokenReplay` — both are dead letters.

Impact: The trust ceremony the spec requires does not exist. Pairing is an
unconditional record creation with no verification step.

### CRITICAL-4: PrincipalId never verified by daemon

The daemon (`daemon.py`) has no concept of principals. The CLI reads the
principal from `store.py` and includes it in spine events, but the daemon HTTP
API never receives, checks, or scopes by principal. Any process can act as any
principal by writing directly to the state files.

### HIGH-1: Hermes adapter is unimplemented

Location: `scripts/hermes_summary_smoke.sh:45-55`

The smoke test directly imports `spine.py` and appends events. No adapter, no
authority token, no capability check. The contract in
`references/hermes-adapter.md` defines `HermesAdapter.connect(authority_token)`
— none of it exists in code.

Any process with filesystem access can append arbitrary events as "Hermes."

### HIGH-2: Shell injection in hermes_summary_smoke.sh

Location: `scripts/hermes_summary_smoke.sh:52`

```bash
event = append_hermes_summary('$SUMMARY_TEXT', ...)
```

`SUMMARY_TEXT` is shell-interpolated into a Python string literal. A value
containing single quotes breaks execution. A crafted value achieves arbitrary
Python code execution. Must use argument passing or stdin, not interpolation.

---

## Pass 2 — Coupled-State and Protocol Surface Review

### STATE-1: Bootstrap is not idempotent

Location: `scripts/bootstrap_home_miner.sh:147-150`

Default bootstrap calls `cli.py bootstrap --device alice-phone`, which calls
`pair_client("alice-phone", ["observe"])`. On re-run, `store.py:100-101` raises
`ValueError("Device 'alice-phone' already paired")` and bootstrap fails.

Plan violation: "bootstrap must either detect existing prepared state and reuse
it safely or wipe and recreate."

### STATE-2: Pairing store and event spine can diverge

Location: `services/home-miner-daemon/cli.py:98-115`

In `cmd_pair()`, the pairing record is created first (line 103), then spine
events are appended (lines 106-115). If event append fails, the pairing record
exists but the spine has no trace of it. No transaction, no rollback.

Additionally, `cmd_bootstrap()` (line 89) appends only `pairing_granted` with
no preceding `pairing_requested`. But `cmd_pair()` appends both. The protocol
is inconsistent — bootstrap creates a pairing without a request event.

### STATE-3: Misleading "rejected" receipts for unreachable daemon

Location: `services/home-miner-daemon/cli.py:155-162`

When `daemon_call` returns `{"error": "daemon_unavailable"}`, the code appends
a `control_receipt` with `status="rejected"`. This is semantically wrong — the
daemon never rejected anything; it was never contacted. The audit trail
misrepresents what happened. Should use a distinct status like `"unreachable"`.

### STATE-4: No control command serialization or conflict detection

The plan requires: "The plan must state how the daemon handles two competing
control requests so the system cannot acknowledge both as if they were
independently applied."

`ThreadedHTTPServer` accepts concurrent requests. Two simultaneous `set_mode`
calls both acquire `self._lock` sequentially and both succeed. No conflict
detection, no `ControlCommandConflict` error. The error class is defined in
`references/error-taxonomy.md` but is dead code.

### STATE-5: Event spine stores plaintext — encryption unimplemented

Location: `services/home-miner-daemon/spine.py:64-65`

Events are written as plaintext JSON to `event-spine.jsonl`. The spec says
"append-only encrypted event journal." The contract says "All payloads are
encrypted using the principal's identity key." This is completely unimplemented.

### STATE-6: Miner state not persisted — staleness undetectable

`MinerSimulator.__init__` holds all state in memory. On restart, miner resets
to stopped/paused/0. Snapshots always carry `datetime.now()` as freshness, so
staleness is never detectable. `MinerSnapshotStale` is unreachable.

---

## Milestone Fit Assessment

### What works

| Area | Status |
|------|--------|
| Repo scaffolding | Complete |
| Reference contracts (5 documents) | Well-defined |
| Upstream manifest + fetch | Working |
| Daemon starts on localhost | Working |
| Miner simulator (start/stop/mode) | Working |
| Gateway client UI shell | Partial (inbox/agent empty) |
| CLI command structure | Working |
| Design doc | Complete |

### What's missing or broken vs plan acceptance criteria

| Plan Requirement | Status |
|-----------------|--------|
| Capability enforcement at daemon | Broken (client-side only) |
| LAN-only binding validation | Broken (0.0.0.0 accepted) |
| Trust ceremony | Missing (tokens never verified) |
| PrincipalId verified on requests | Missing (daemon unaware) |
| Event spine encryption | Missing (plaintext) |
| Hermes adapter implementation | Missing (direct writes) |
| Idempotent bootstrap | Broken (fails on re-run) |
| Control command serialization | Missing (no conflict detection) |
| Stale snapshot detection | Missing (always fresh) |
| Inbox display in gateway client | Missing (empty stub) |
| Automated tests | Missing (zero test files) |
| gateway-proof.md | Missing (not created) |
| onboarding-storyboard.md | Missing (not created) |
| Structured logging | Missing (logging suppressed) |
| DESIGN.md color alignment | Broken (Tailwind Stone, not spec palette) |

### Design system divergence

The HTML client uses a light-mode palette from Tailwind's Stone scale:
`#FAFAF9`, `#FFFFFF`, `#1C1917`, `#15803D`, `#B91C1C`, `#B45309`.

DESIGN.md specifies: Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`,
Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`.

None of the DESIGN.md colors appear in the implementation.

---

## Prioritized Fix List

### Must fix before approval (security/correctness)

1. Move capability enforcement into the daemon HTTP layer — reject
   unauthenticated control requests
2. Validate bind address against a private-address allowlist; reject 0.0.0.0
3. Implement real token verification: expiration check, replay detection,
   token_used flag
4. Fix bootstrap idempotency: detect existing pairing and skip or update
5. Fix event-ordering inconsistency between cmd_bootstrap and cmd_pair
6. Use distinct receipt status for unreachable vs rejected daemon
7. Fix shell injection in hermes_summary_smoke.sh

### Must fix before milestone-1 acceptance (spec compliance)

8. Implement encrypted payloads or explicitly amend the spec to defer
   encryption to a later milestone with documented rationale
9. Implement stale snapshot detection with a configurable freshness threshold
10. Implement control command conflict detection
11. Add tests: pairing replay, capability enforcement, bootstrap idempotency
12. Implement inbox event display in the gateway client
13. Align color system with DESIGN.md
14. Add structured logging per observability contract

### Should fix (quality/completeness)

15. Persist miner state to disk for restart recovery
16. Create gateway-proof.md and onboarding-storyboard.md
17. Implement Hermes adapter with authority token verification
18. Replace no-local-hashing audit source-grep stub with process inspection

---

## Frontier Tasks Updated

After this review, the frontier tasks from the plan are augmented:

- Add automated tests for error scenarios: BLOCKED by daemon auth (fix 1 first)
- Add tests for trust ceremony, Hermes delegation, event spine routing:
  BLOCKED by fixes 1, 3, 5, 17
- Document gateway proof transcripts: BLOCKED by daemon not passing audit
- Implement Hermes adapter: actionable after fix 1
- Implement encrypted operations inbox: BLOCKED by fix 8 (encryption)
- Restrict to LAN-only with formal verification: BLOCKED by fix 2

## Conclusion

The contracts and scaffolding are solid. The spec, plan, design doc, error
taxonomy, and observability contract are well-written and internally consistent.
The gap is between what the contracts promise and what the code enforces. The
daemon is a trust-free HTTP server that ignores the entire capability model
built around it. Fixing this requires moving auth into the daemon — not a
rewrite, but a structural change that touches every endpoint.

The prior review's APPROVED verdict is overridden. This lane is rejected until
fixes 1-7 are applied and verified.
