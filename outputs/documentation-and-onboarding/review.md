# Documentation & Onboarding Lane — Review

**Status:** REJECTED — total lane failure
**Reviewed:** 2026-03-22
**Reviewer:** claude-opus-4-6

## Verdict

The documentation-and-onboarding lane produced zero artifacts. The specify
stage reported "success" but the MiniMax-M2.7-highspeed model processed 0
tokens in and 0 tokens out. Neither `outputs/documentation-and-onboarding/spec.md`
nor any of the six frontier deliverables exist. The `outputs/documentation-and-onboarding/`
directory was never created.

**This is a false-positive success.** The pipeline trusted process exit code
rather than verifying artifact existence as a postcondition.

## Artifact Inventory

| Required Artifact | Exists | Notes |
|---|---|---|
| `outputs/documentation-and-onboarding/spec.md` | NO | Never created |
| `outputs/documentation-and-onboarding/review.md` | YES | This file (reviewer-created) |
| Rewritten `README.md` | NO | Still contains original brief description |
| `docs/contributor-guide.md` | NO | Never created |
| `docs/operator-quickstart.md` | NO | Never created |
| `docs/api-reference.md` | NO | Never created |
| `docs/architecture.md` | NO | Never created |
| Clean-machine verification | NO | Nothing to verify |

## Milestone Fit

The documentation lane was supposed to produce the onboarding surface for the
first Zend product slice. The home-command-center lane has already delivered
working code (daemon, CLI, gateway client, scripts, contracts). That code is
undocumented. A contributor cloning this repo today would need to read the
ExecPlan, the product spec, and the source code to understand what exists and
how to run it.

This gap is real and growing. The longer implementation proceeds without
onboarding documentation, the harder it becomes to write accurate docs — the
codebase moves and the docs must chase it.

## Remaining Blockers

1. **Pipeline bug**: The fabro runner must gate lane success on artifact
   existence, not on model process exit code. Until this is fixed, any model
   that exits cleanly without producing output will be marked "success."

2. **Spec must be written first**: The documentation lane needs its own spec
   (`outputs/documentation-and-onboarding/spec.md`) before any docs are
   authored. The spec should define the audience (contributor vs. operator vs.
   agent), the accuracy contract (every command must be runnable), and the
   maintenance boundary (which docs are living vs. snapshot).

3. **Implementation must be verified first**: Several frontier tasks assume
   verified behavior (API reference, operator quickstart). The
   home-command-center review itself notes that the daemon has never been
   tested end-to-end. Documenting unverified behavior risks producing
   dishonest documentation.

---

## Nemesis Pass 1 — First-Principles Trust Boundary Challenge

The documentation lane produced nothing to review directly, but any future
documentation must honestly represent the security posture of the existing
implementation. The following findings affect what documentation can truthfully
claim.

### F1. HTTP daemon has no authentication

The `GatewayHandler` in `services/home-miner-daemon/daemon.py` accepts
unauthenticated requests on all endpoints (`/health`, `/status`,
`/miner/start`, `/miner/stop`, `/miner/set_mode`). Any process that can reach
the bound address can start, stop, or reconfigure the miner.

The capability model (`observe` vs. `control`) is enforced only in the CLI
layer (`cli.py`), not at the HTTP layer. A direct `curl` to `/miner/stop`
bypasses all capability checks. Documentation must not describe the capability
model as a security boundary — it is a CLI-layer convenience, not an
enforcement point.

**Impact:** Any documentation claiming "observe-only clients cannot control the
miner" would be false for HTTP-level access.

### F2. BIND_HOST is operator-overridable without guardrails

`daemon.py:34` reads `ZEND_BIND_HOST` from the environment, defaulting to
`127.0.0.1`. Setting it to `0.0.0.0` exposes an unauthenticated miner control
surface to the entire network. Combined with F1, this means any device on the
LAN — or the internet if port-forwarded — can control the miner.

**Impact:** Operator quickstart documentation must include a prominent warning
about bind-host configuration. The spec calls this "LAN-only" but the
implementation only achieves this by default, not by enforcement.

### F3. Pairing tokens are non-functional

`store.py:86-89` creates pairing tokens with an expiration set to
`datetime.now()` — every token expires at the instant of creation. The token is
stored in the pairing record but never validated on any subsequent request. The
entire pairing ceremony is cosmetic.

**Impact:** Documentation cannot describe pairing as a trust ceremony that
"proves" device authorization. It is a naming step with no cryptographic or
temporal validation.

### F4. Event spine is plaintext, not encrypted

`spine.py` writes events as plaintext JSON to `event-spine.jsonl`. The product
spec and architecture documents call this an "encrypted event journal" and an
"encrypted operations inbox." No encryption exists.

**Impact:** Documentation must not use the word "encrypted" to describe the
current event spine. This is the most significant honesty gap between the spec
and the implementation.

### F5. State directory permissions are uncontrolled

`os.makedirs(STATE_DIR, exist_ok=True)` creates the state directory with
default umask permissions. On a multi-user system, other users may be able to
read principal identity, pairing records, and all event spine data. On a
single-user Raspberry Pi this is less critical, but the operator quickstart
should document the assumption.

### F6. PID file can be hijacked

`bootstrap_home_miner.sh` reads `state/daemon.pid` and sends `kill` signals to
whatever PID it contains. A malicious or buggy actor that writes a different
PID into this file can cause the bootstrap script to kill an arbitrary process.
On single-user home hardware this is low-severity, but documentation should not
describe the daemon lifecycle as "safe" without qualification.

---

## Nemesis Pass 2 — Coupled-State Review

### S1. CLI capability enforcement is decoupled from HTTP enforcement

The capability model exists in two layers that do not agree:

- `cli.py` checks `has_capability(device, 'control')` before calling the
  daemon
- `daemon.py` accepts all requests without any capability check

These two surfaces are coupled in intent but decoupled in enforcement. Every
mutation path through the daemon is unguarded. The CLI is the only gate, and
it is trivially bypassed.

**Consistency requirement:** Either move capability enforcement into the daemon
(check pairing token on every request) or document that the daemon is an
unprotected internal service that must never be network-exposed.

### S2. Pairing store and event spine can diverge on crash

In `cli.py:cmd_pair()`, the pairing record is written to `pairing-store.json`
first (via `pair_client()`), then two spine events are appended. If the process
crashes between store write and spine append:

- The device is paired (store has the record)
- The spine has no record of the pairing
- The inbox will never show the pairing approval

This is a silent inconsistency. The spec says the event spine is the "source of
truth," but the store can contain state the spine doesn't know about.

### S3. Miner state and control receipt can diverge

In `cli.py:cmd_control()`, the daemon processes the action first (via HTTP),
then a control receipt is appended to the spine. If the spine write fails
(disk full, permissions, crash), the miner state changed without an audit
trail. The inbox will not show the action.

### S4. Principal creation is not atomic

`store.py:load_or_create_principal()` checks for file existence, then creates
and writes. Two concurrent callers can both find the file missing, both create
a principal, and the second write silently overwrites the first. Any pairing
records created by the first caller reference an orphaned principal ID.

On single-process usage this is unlikely but documentation or operator guides
should not describe the principal as "stable" without noting this race.

### S5. Bootstrap is not idempotent

The bootstrap script calls `stop_daemon`, `start_daemon`, then
`bootstrap_principal`. Stopping and starting the daemon does not clear state
files. If `alice-phone` was already paired in a prior run,
`bootstrap_principal` calls `pair_client("alice-phone")` which raises
`ValueError("Device 'alice-phone' already paired")`. Bootstrap fails on second
run.

The PLANS.md requirement says steps should be "idempotent and safe" and
"runnable multiple times without damage." Bootstrap violates this.

### S6. No replay protection on control commands

Control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`) carry no
nonce, timestamp, or sequence number. A replayed HTTP request is
indistinguishable from a new one. In the current LAN-only simulator this is low
risk, but it violates the spec's intent around explicit acknowledgments.

---

## Recommendations

### For the fabro pipeline

1. Gate lane success on artifact existence, not process exit code.
2. Log model token counts and fail if both are zero.

### For the documentation lane retry

1. Write `outputs/documentation-and-onboarding/spec.md` first, defining
   audience, accuracy contract, and maintenance boundary.
2. Verify the daemon actually runs before documenting its behavior.
3. Be honest about what "encrypted" and "capability-scoped" mean in the current
   implementation vs. the target spec.
4. The operator quickstart must include bind-host warnings and state-directory
   permission guidance.
5. The API reference must note that the HTTP layer has no authentication and
   that capability checks exist only in the CLI.

### For the implementation (prerequisites to honest documentation)

1. Move capability enforcement into the daemon HTTP layer.
2. Fix `create_pairing_token()` to set a real expiration.
3. Make bootstrap idempotent (skip pairing if device already exists).
4. Add at minimum file-level encryption to the event spine, or stop calling it
   "encrypted" in all documentation and specs.
