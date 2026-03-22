# Documentation & Onboarding Lane — Review

**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-22
**Lane:** documentation-and-onboarding
**Specify stage:** MiniMax-M2.7-highspeed — 0 tokens in / 0 tokens out
**Verdict:** BLOCKED — specify stage produced no artifacts

---

## 1. Lane Status

The specify stage reported "success" but generated nothing. The required artifact
`outputs/documentation-and-onboarding/spec.md` did not exist when this review
began. A placeholder has been written to record this failure.

**Root cause:** The pipeline treats a clean process exit as success. It does not
validate that the model produced output or that required artifacts exist on disk.
This is a fabro orchestration gap — exit code 0 is not evidence of work.

**None of the six frontier tasks were attempted:**

| Frontier Task | Status |
|---|---|
| Rewrite README.md with quickstart and architecture overview | NOT STARTED |
| Create docs/contributor-guide.md with dev setup instructions | NOT STARTED |
| Create docs/operator-quickstart.md for home hardware deployment | NOT STARTED |
| Create docs/api-reference.md with all endpoints documented | NOT STARTED |
| Create docs/architecture.md with system diagrams and module explanations | NOT STARTED |
| Verify documentation accuracy by following it on a clean machine | NOT STARTED |

---

## 2. Correctness Assessment of the Existing Codebase

Since the documentation lane is supposed to describe what exists, this section
reviews the accuracy and completeness of the codebase the docs would cover.

### 2.1 What exists and works

The milestone 1 implementation is structurally complete as a simulator:

- **Daemon** (`services/home-miner-daemon/daemon.py`): HTTP server on
  `127.0.0.1:8080` with `/health`, `/status`, `/miner/start`, `/miner/stop`,
  `/miner/set_mode` endpoints. Threaded, uses a global `MinerSimulator`.
- **CLI** (`services/home-miner-daemon/cli.py`): `bootstrap`, `pair`, `status`,
  `health`, `control`, `events` subcommands.
- **Store** (`services/home-miner-daemon/store.py`): JSON-file-based principal
  and pairing persistence in `state/`.
- **Event spine** (`services/home-miner-daemon/spine.py`): JSONL append-only
  journal in `state/event-spine.jsonl`.
- **Gateway UI** (`apps/zend-home-gateway/index.html`): Single-page mobile-first
  UI with status hero, mode switcher, start/stop, inbox, agent, and device
  screens. Polls `/status` every 5 seconds.
- **Shell scripts** (`scripts/`): Bootstrap, pairing, status reading, mode
  setting, upstream fetch, Hermes smoke test, local-hashing audit.
- **Reference contracts** (`references/`): Event spine, inbox, Hermes adapter,
  error taxonomy, observability, design checklist.

### 2.2 README accuracy

The current `README.md` describes Zend as a "canonical planning repository" with
no implementation code. This is now false — the repo contains a working daemon,
CLI, UI, scripts, and reference contracts. The README urgently needs rewriting.

### 2.3 Contract vs implementation drift

| Contract claim | Implementation reality |
|---|---|
| Event payloads are "encrypted" (event-spine.md, inbox-contract.md) | Plaintext JSON written to `event-spine.jsonl` — no encryption |
| Pairing token has expiration and single-use (inbox-contract.md) | Token expiration is set to `datetime.now()` at creation (already expired). `token_used` is never checked or updated |
| `pairing_granted` payload includes `pairing_token` (event-spine.md) | `append_pairing_granted()` writes `granted_capabilities` but no `pairing_token` field |
| Error taxonomy defines 10 error codes | Daemon uses ad-hoc strings (`already_running`, `invalid_json`, `not_found`) — none from the taxonomy |
| Observability contract defines structured log events and metrics | Daemon suppresses all HTTP logging (`log_message` returns nothing). No structured events emitted |
| Hermes adapter interface defined in TypeScript | No Hermes adapter implementation exists |

### 2.4 Milestone fit

The product spec acceptance criteria require:

- [x] New contributor understands Zend is a private command center — partially,
  via specs and design doc (README contradicts this)
- [x] First slice proves mobile/script gateway without on-device mining
- [x] Thin mobile-shaped command-center experience (index.html exists)
- [x] Shared PrincipalId contract
- [x] Encrypted operations inbox backed by event spine — **FAIL: not encrypted**
- [ ] Hermes Gateway connects through Zend adapter — not implemented
- [x] LAN-only binding
- [x] Observe/control capability scopes exist
- [ ] Encrypted transport never requires plaintext on server surfaces — **FAIL:
  everything is plaintext**

---

## 3. Nemesis Pass 1 — First-Principles Trust & Authority Challenge

### 3.1 No authentication on the HTTP API

**Severity: CRITICAL (for any non-localhost deployment)**

The daemon HTTP endpoints have zero authentication. The CLI checks
`has_capability()` before calling the daemon, but this is a client-side courtesy.
Any process on the same machine (or network, if `ZEND_BIND_HOST` is changed) can:

```
curl http://127.0.0.1:8080/miner/start -X POST
curl http://127.0.0.1:8080/miner/set_mode -X POST -d '{"mode":"performance"}'
curl http://127.0.0.1:8080/miner/stop -X POST
```

The capability model (`observe` vs `control`) is enforced only in `cli.py`, not
in the daemon. The trust boundary the spec describes does not exist at the API
layer.

**Risk:** In a documentation context, if the operator quickstart tells someone
to bind to a LAN interface for multi-device access, every device on the LAN gets
full unauthenticated control. The docs would need to scream this limitation.

### 3.2 PrincipalId has no cryptographic binding

`PrincipalId` is a random UUID stored in `state/principal.json`. It is not
derived from any key material. Any process that can read the file can claim to
be the principal. There is no challenge, no signature, no proof of possession.

For milestone 1 (single-user, localhost), this is acceptable. But documentation
must not describe PrincipalId as providing "identity" or "trust" without
qualifying that it is currently a filesystem-local label, not a cryptographic
identity.

### 3.3 Who can trigger dangerous actions

| Action | Who can trigger | Gate |
|---|---|---|
| Start mining | Any local HTTP client | None |
| Stop mining | Any local HTTP client | None |
| Change mining mode | Any local HTTP client | None |
| Create principal | Any process with filesystem write | None |
| Pair a device | Any process with filesystem write | Duplicate device name check only |
| Append to event spine | Any process with filesystem write | None |
| Read all events | Any local HTTP client (via CLI `events`) | CLI checks observe capability; daemon does not expose events via HTTP |

### 3.4 Pairing ceremony is cosmetic

The spec says "milestone 1 includes a first-class trust ceremony" and "pairing
must feel safe, named, and revocable." The implementation:

- Creates a UUID "token" that expires at creation time
- Never validates the token on subsequent requests
- Never checks `token_used`
- Has no revocation path (no `unpair` command exists)

The pairing store records who was paired, but the record gates nothing at the
HTTP layer. Documentation should be honest: this is a device registry, not a
trust ceremony.

---

## 4. Nemesis Pass 2 — Coupled-State & Mutation Consistency

### 4.1 Spine/store dual-write without atomicity

`cmd_pair()` in `cli.py` executes:
1. `pair_client()` → writes `pairing-store.json`
2. `spine.append_pairing_requested()` → appends to `event-spine.jsonl`
3. `spine.append_pairing_granted()` → appends to `event-spine.jsonl`

If the process crashes between step 1 and step 2, the pairing exists but the
spine has no record. The invariant "event spine is the source of truth" is
violated. The store and spine can diverge on any crash or interrupt.

`cmd_bootstrap()` is different: it calls `pair_client()` then only
`spine.append_pairing_granted()` (no `pairing_requested` event). So bootstrap
devices have a different spine trace than subsequently paired devices. This
asymmetry is undocumented.

### 4.2 File-based concurrency without locking

`store.py` and `spine.py` use read-modify-write on JSON files without file
locks. The daemon uses `ThreadingMixIn` for concurrent HTTP handling. If two
concurrent requests trigger pairing (unlikely but possible via scripts), both
read the same pairing store, both find no duplicate, both write — one overwrites
the other.

`spine.py` appends to JSONL (append-only), which is safer but not guaranteed
atomic on all filesystems (a partial line write on crash produces corrupt JSONL).

### 4.3 MinerSimulator state vs spine divergence

The daemon's `MinerSimulator` maintains in-memory state (`_status`, `_mode`,
`_hashrate_hs`). The CLI writes control receipts to the spine. But:

- The daemon has no awareness of the spine
- The spine has no awareness of the daemon's actual state
- If the daemon restarts, all in-memory state resets to `STOPPED`/`PAUSED` but
  the spine still contains receipts claiming `RUNNING`/`PERFORMANCE`

There is no reconciliation path. The spine claims the miner was started; the
daemon says it's stopped. Documentation must warn operators that daemon restart
resets miner state without a corresponding spine event.

### 4.4 Bootstrap idempotence

Running `bootstrap` twice with the same device name:
1. First call: creates principal, creates pairing, writes spine event — succeeds
2. Second call: `pair_client()` raises `ValueError("Device 'alice-phone' already
   paired")` — fails

The first call's spine events are already written. There is no cleanup, no
rollback, no idempotent retry. The `--stop` / restart cycle requires manual
`state/` cleanup. Documentation must cover this recovery path.

### 4.5 Gateway UI hardcoded capabilities

`index.html` line 627: `capabilities: ['observe', 'control']` is hardcoded in
the client-side state. The UI does not read capabilities from the server or
from the pairing store. An observe-only paired device will still show start/stop
buttons; the client-side check at line 711 (`state.capabilities.includes('control')`)
always passes because capabilities are hardcoded to include `control`.

### 4.6 No CORS headers on daemon

The gateway UI at `index.html` makes `fetch()` calls to `http://127.0.0.1:8080`.
If served from a different origin (even `file://`), browsers may block these
requests. The daemon sets no CORS headers. This will break the documented
workflow unless the UI is served from the daemon itself (which it currently is
not — no static file serving exists).

---

## 5. Remaining Blockers for Documentation Lane

### 5.1 Pipeline blocker

The specify stage must actually produce a spec. Options:
1. Re-run with a model that produces output
2. Write the spec manually
3. Skip the specify stage and write docs directly

### 5.2 Content blockers

Before documentation can be honest and accurate:

1. **README.md** is actively misleading — says "no implementation code" when
   implementation exists
2. **Encryption claims** need to be either implemented or documented as "planned,
   not yet implemented"
3. **Capability enforcement** needs to be documented as CLI-only, not API-level
4. **CORS/serving** needs a solution before the operator quickstart can describe
   how to use the gateway UI
5. **Error taxonomy** is not implemented — docs should reference it as a contract,
   not as current behavior
6. **Observability** is not implemented — docs should not claim structured logging
   exists

### 5.3 Documentation that can be written now

Despite the above, useful and honest documentation is possible:

- **Architecture overview**: The component layout (daemon, CLI, store, spine, UI,
  scripts) is clear and stable
- **API reference**: The five HTTP endpoints are well-defined and testable
- **CLI reference**: The six subcommands with their arguments are documented in
  argparse and can be extracted
- **Quickstart**: `scripts/bootstrap_home_miner.sh` works and is the correct
  entry point
- **Contributor guide**: Python 3, no external dependencies, file-based state,
  clear module boundaries

### 5.4 What the docs must NOT claim

- That the system provides encryption (it does not)
- That capability scoping prevents unauthorized control (it does not at the API
  layer)
- That the pairing ceremony provides trust (it provides a device registry)
- That the event spine is the authoritative source of truth (it can diverge from
  the store and the daemon state)
- That observability or structured logging exists (the contract is written, the
  implementation is not)

---

## 6. Recommendations

1. **Re-run specify** with a model that produces output, or skip it and write
   docs directly from codebase analysis
2. **Rewrite README.md first** — it is the highest-signal artifact and is
   currently wrong
3. **Add a "Known Limitations" section** to every doc that covers the gap between
   contract and implementation
4. **Add CORS headers** to the daemon before writing the operator quickstart,
   or have the daemon serve `index.html` directly
5. **Document the state cleanup path** (`rm -rf state/`) as the recovery
   mechanism for bootstrap failures
6. **Consider adding daemon-side capability enforcement** before documenting the
   security model — or document honestly that it is client-side only

---

## 7. Summary

The documentation-and-onboarding lane is fully blocked: the specify stage
produced nothing, and zero frontier tasks were attempted. The underlying
codebase is structurally sound for a milestone 1 simulator but has significant
gaps between its contracts and implementation, particularly around encryption,
authentication, and observability. Documentation written for this codebase must
be honest about these gaps rather than echoing the aspirational language of the
reference contracts.
