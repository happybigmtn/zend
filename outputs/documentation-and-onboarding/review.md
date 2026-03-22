# Documentation & Onboarding — Review

**Lane:** documentation-and-onboarding
**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-22
**Verdict:** REVISE — correctness failures block merge

---

## Summary

The documentation lane produced five artifacts: a rewritten README.md, docs/contributor-guide.md, docs/operator-quickstart.md, docs/api-reference.md, and docs/architecture.md. The writing quality is high — prose is clear, structure is logical, and the tone matches the project's identity. However, verification against source code reveals multiple factual errors that would break a newcomer's first session. The required output artifacts (`outputs/documentation-and-onboarding/spec.md` and `outputs/documentation-and-onboarding/review.md`) were not produced by the specify stage.

---

## 1. Correctness Failures

### 1.1 — Phantom API Endpoints (BLOCKING)

`docs/api-reference.md` documents three endpoints that do not exist in `daemon.py`:

| Documented Endpoint | Exists in daemon.py? | Notes |
|---|---|---|
| `GET /spine/events` | NO | daemon.py only routes `/health` and `/status` in `do_GET` |
| `GET /metrics` | NO | No metrics handler exists anywhere |
| `POST /pairing/refresh` | NO | No pairing handler exists in daemon |

The daemon's `GatewayHandler.do_GET()` (daemon.py:168-174) handles only `/health` and `/status`. Everything else returns 404. The API reference fabricated three endpoints from type signatures and naming conventions.

**Impact:** Any operator or contributor who curls these endpoints gets `{"error": "not_found"}`. The entire "spine/events" section of the API reference is fiction.

### 1.2 — Phantom CLI Subcommand (BLOCKING)

`docs/operator-quickstart.md` §7 documents:

```
python3 services/home-miner-daemon/cli.py devices
```

No `devices` subcommand exists in `cli.py`. The function `store.list_devices()` exists but is never wired into the CLI's argparse subparsers (cli.py:204-237).

### 1.3 — README Quickstart Step 5 Fails (BLOCKING)

README.md step 5 runs:

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

But step 2 (`bootstrap_home_miner.sh`) pairs `alice-phone` with `["observe"]` only (cli.py:78). The control command requires `control` capability (cli.py:134). This returns `{"error": "unauthorized"}`, not the documented success response.

A newcomer following the quickstart verbatim hits an auth error on step 5 of 5.

### 1.4 — `source .env` Does Not Export Variables

`docs/operator-quickstart.md` §4 instructs:

```bash
source .env
python3 services/home-miner-daemon/daemon.py &
```

The `.env` format shown uses bare assignments (`ZEND_BIND_HOST=192.168.1.100`) without `export`. `source .env` sets shell variables, not environment variables. Python's `os.environ.get()` will not see them. The daemon will bind to `127.0.0.1` (the default), not the configured LAN IP.

Fix: either prefix assignments with `export` in the .env template, or instruct `set -a; source .env; set +a`.

### 1.5 — "Encrypted" Event Journal Is Not Encrypted

`spine.py` docstring (line 2) says "append-only encrypted event journal." `docs/architecture.md` §2 repeats "Append-only encrypted event journal." Events are written as plaintext JSON via `json.dumps()` (spine.py:65). No encryption exists. The word "encrypted" is a forward-looking aspiration presented as current fact.

### 1.6 — README Directory Structure Lists `scripts/` Twice

README.md lines 99-114 show two separate `scripts/` blocks. The second one (lines 107-108) documents `fetch_upstreams.sh` under a duplicate heading.

### 1.7 — CORS Not Documented

The HTML gateway (`index.html`) fetches from `http://127.0.0.1:8080` (line 632). When served from a different origin (e.g., `http://192.168.1.100:8081` per operator-quickstart §6 Option B), the browser will block requests due to missing CORS headers. The daemon sets no `Access-Control-Allow-Origin` header. Neither the operator guide nor the API reference mentions this.

---

## 2. Milestone Fit

### Frontier Tasks Checklist

| Task | Status | Notes |
|---|---|---|
| Rewrite README.md with quickstart and architecture overview | DONE with errors | Quickstart step 5 fails; duplicate `scripts/` section |
| Create docs/contributor-guide.md | DONE | Accurate and thorough |
| Create docs/operator-quickstart.md | DONE with errors | Phantom `devices` command; `.env` sourcing bug; CORS omission |
| Create docs/api-reference.md | DONE with errors | 3 phantom endpoints; error taxonomy includes unimplemented codes |
| Create docs/architecture.md | DONE with minor errors | "Encrypted" claim; Request Lifecycle diagram shows `PairingTokenExpired` validation that doesn't exist |
| Verify documentation accuracy on clean machine | NOT DONE | Errors prove this step was skipped |

### Required Artifacts

| Artifact | Status |
|---|---|
| `outputs/documentation-and-onboarding/spec.md` | MISSING |
| `outputs/documentation-and-onboarding/review.md` | MISSING (this file is the review) |

---

## 3. Nemesis Security Review

### Pass 1 — First-Principles Challenge

#### 3.1 — The Daemon Has No Auth

The entire authorization model lives in the CLI layer (cli.py:47-48, 134). The daemon's HTTP endpoints are completely unprotected. Any device on the LAN can:

```bash
curl -X POST http://192.168.1.100:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

No pairing token, no capability check, no client identification. The CLI's `has_capability()` check is a convenience gate, not a security boundary. The docs partially acknowledge this ("authorization is enforced at the CLI layer") but operator-quickstart.md does not make clear that **the HTTP API itself is wide open to the LAN**.

**Risk:** On shared networks (apartment buildings, guest Wi-Fi, compromised IoT devices), any LAN peer can control the miner. The operator guide should state this explicitly and recommend firewall rules.

#### 3.2 — Pairing Tokens Are Cosmetic

`store.create_pairing_token()` (store.py:86-90) creates a token and sets `expires` to `datetime.now()` — the token expires at the instant of creation. `token_used` is initialized to `False` and never updated. No code path ever validates, refreshes, or revokes a token.

The API reference documents `POST /pairing/refresh` and planned error codes (`PairingTokenExpired`, `PairingTokenReplay`) that have no implementation. The token system is scaffolded data with no enforcement.

#### 3.3 — PrincipalId Has No Cryptographic Binding

`PrincipalId` is `uuid.uuid4()` — a random UUID with no signing key, no challenge-response, no attestation. Anyone who reads `state/principal.json` (or guesses the UUID format) can impersonate the principal. Since the daemon doesn't check principals at all on HTTP requests, this is moot in milestone 1, but the architecture docs present `PrincipalId` as an identity primitive without noting its lack of cryptographic strength.

#### 3.4 — LAN = Trusted Is Fragile

The security model assumes the LAN is trusted. Operator-quickstart §9 says "do not change ZEND_BIND_HOST to 0.0.0.0" but does not recommend:
- Firewall rules (e.g., `ufw allow from 192.168.1.0/24 to any port 8080`)
- Binding to a specific interface rather than an IP (IPs can change via DHCP)
- mDNS/Avahi considerations (the daemon could be discovered by name)

### Pass 2 — Coupled-State Review

#### 3.5 — Store and Spine Are Not Transactionally Coupled

In `cmd_pair()` (cli.py:98-128):
1. `pair_client()` writes to `pairing-store.json`
2. `append_pairing_requested()` appends to `event-spine.jsonl`
3. `append_pairing_granted()` appends to `event-spine.jsonl`

A crash between step 1 and step 2 leaves a paired device with no spine record. A crash between step 2 and step 3 leaves a "requested" event with no "granted" event. No recovery mechanism exists. The spine is described as "source of truth" but can diverge from the store.

#### 3.6 — State File Writes Are Not Atomic

`save_pairings()` (store.py:80-83) writes directly to `pairing-store.json` via `json.dump()`. A crash or power loss during write corrupts the file. The standard pattern (write to temp file, fsync, rename) is not used. Same issue with `_save_event()` — a partial line in the JSONL file will cause `json.loads()` to throw on the next `_load_events()` call, breaking all spine reads.

#### 3.7 — No File Locking on State Files

Two concurrent CLI processes can race on `pairing-store.json`. Both read, both append their pairing, last writer wins — losing the other's record. The daemon itself is single-process but the CLI can be invoked concurrently (e.g., two terminal windows, or the bootstrap script racing with a manual pair).

#### 3.8 — Event Spine Has No Integrity Protection

No checksums, no sequence numbers, no HMAC. An attacker with filesystem access (or a buggy concurrent writer) can:
- Append fake events
- Truncate the file
- Modify historical entries

The spine is positioned as an audit trail but provides no tamper evidence.

### Operator Safety

#### 3.9 — Bootstrap Is Not Idempotent

Running `bootstrap_home_miner.sh` twice for the same device name hits `ValueError` from `pair_client()` ("Device 'alice-phone' already paired"). The script does not check for existing state before attempting to pair. An operator who re-runs bootstrap after a partial failure gets an error with no recovery guidance.

#### 3.10 — `kill -9` in Bootstrap Script

`bootstrap_home_miner.sh` line 54 sends `SIGKILL` after only 1 second of `SIGTERM`. `SIGKILL` bypasses Python's `KeyboardInterrupt` handler and `server.shutdown()`. If the daemon is mid-write to a state file, `SIGKILL` can corrupt it. The grace period should be longer (5-10 seconds), and the script should verify the process actually exited before escalating.

#### 3.11 — `rm -rf state/` as Recovery

Operator-quickstart §8 recommends `rm -rf /opt/zend-home/state` as the primary recovery action. This destroys:
- PrincipalId (all paired devices lose their identity binding)
- All pairing records (every device must re-pair)
- The entire event spine (audit history gone)

The backup instruction (`cp -r`) precedes this but is easily skipped. Recovery should default to repairing the specific corrupt file, not nuclear deletion.

---

## 4. What's Good

- **contributor-guide.md** is the strongest document. Dev setup, coding conventions, plan-driven development, and the design system summary are accurate and well-organized.
- **architecture.md** ASCII diagrams are clear and correctly represent the actual module relationships (modulo the "encrypted" claim and phantom validation steps).
- **README.md** structure is clean — quickstart, architecture diagram, directory tree, env vars, and doc links. The shape is right even if some content is wrong.
- **operator-quickstart.md** systemd unit file and troubleshooting section are practical and operator-friendly.
- **Design system** is correctly summarized in contributor-guide.md without losing the essential constraints from DESIGN.md.

---

## 5. Remaining Blockers

### Must Fix Before Merge

1. Remove phantom endpoints from api-reference.md (`GET /spine/events`, `GET /metrics`, `POST /pairing/refresh`) or implement them
2. Remove `cli.py devices` reference from operator-quickstart.md or implement the subcommand
3. Fix README quickstart step 5 — either grant `control` capability at bootstrap or add a pairing step before the control command
4. Fix `.env` sourcing — use `export` or document `set -a`
5. Remove "encrypted" from spine.py docstring and architecture.md (or implement encryption)
6. Fix duplicate `scripts/` section in README directory structure
7. Document CORS limitation for LAN-served HTML gateway
8. Add note to operator-quickstart §9 that the daemon HTTP API itself has no auth — LAN access = full control

### Should Fix

9. Document that bootstrap is not idempotent; add `--force` flag or existence check
10. Replace `kill -9` with longer grace period in bootstrap script
11. Remove planned/unimplemented error codes from api-reference.md error table, or clearly mark them as "(not yet implemented)"
12. Note in architecture.md §4 that pairing tokens are scaffolded but not enforced

### Nice to Have

13. Add CORS headers to daemon.py for LAN-served HTML
14. Atomic writes for state files (temp + rename)
15. File locking for concurrent CLI access

---

## 6. Verdict

**REVISE.** The documentation reads well but fails the "follow it on a clean machine" test. Three phantom endpoints, a broken quickstart, and a non-functional `.env` pattern mean a newcomer will hit errors within minutes. The security narrative ("encrypted journal", "pairing tokens", "capability checks") overstates what milestone 1 actually enforces, which could mislead both operators and future contributors about the actual trust boundaries.

Fix the eight blocking items, then re-review.
