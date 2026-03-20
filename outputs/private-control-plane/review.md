# Private Control Plane Review

**Status:** Honest milestone 1 slice review
**Generated:** 2026-03-20

## Verdict

Conditionally approved as a reviewed contract slice, not as a completed
production slice.

The repository already contains a meaningful first implementation for pairing,
event append, and a thin gateway UI, but the secure private-control-plane claim
is only partially true today. The contract in
`outputs/private-control-plane/control-plane-contract.md` is specific enough to
guide the next implementation pass. The current code is not yet strong enough
to mark milestone 1 complete.

## Findings

### 1. High - State durability is split across two roots

Evidence:

- `scripts/bootstrap_home_miner.sh` exports `ZEND_STATE_DIR` to repo-level
  `state/` and writes `state/daemon.pid`
- `services/home-miner-daemon/store.py` and
  `services/home-miner-daemon/spine.py` fall back to cwd-relative `state/`
- the review run produced `state/daemon.pid` and separate durable records under
  `services/home-miner-daemon/state/`

Impact:

- the daemon pid, principal record, pairing records, and event spine are not
  guaranteed to share one canonical recovery path
- `rm -rf state/*` from the plan would not actually reset pairings or the spine

Recommendation:

- require every entry point to share one exported `ZEND_STATE_DIR`
- remove cwd-relative fallback before claiming durable bootstrap or recovery

### 2. High - Observe access is not actually enforced for read paths

Evidence:

- `scripts/read_miner_status.sh` accepts `--client` but never uses it for
  authorization
- `services/home-miner-daemon/cli.py` implements `cmd_status` without checking
  pairing or capability state
- `apps/zend-home-gateway/index.html` hard-codes
  `capabilities: ['observe', 'control']` in browser state

Impact:

- the code defines capability-scoped pairings, but read access is still
  effectively unauthenticated at the script and UI layers
- `observe` is a documented permission more than an enforced boundary

Recommendation:

- require an active pairing with `observe` for status and inbox reads
- hydrate the gateway UI from the pairing store or a session contract instead of
  hard-coded capability state

### 3. High - The event spine is append-only, but not yet private

Evidence:

- `services/home-miner-daemon/state/event-spine.jsonl` stores plaintext JSON
  payloads for pairing, control receipts, and Hermes summaries
- `services/home-miner-daemon/spine.py` writes `payload` objects directly to the
  file without encryption

Impact:

- the current implementation proves one journal and one routing path
- it does not yet satisfy the accepted product claim of a private event spine

Recommendation:

- do not describe the spine as implemented privacy-wise until payload encryption
  or encrypted payload indirection exists
- keep the reviewed contract's `ciphertext` requirement as a real blocker for
  milestone completion

### 4. Medium - Pairing token and expiry semantics are not credible yet

Evidence:

- `services/home-miner-daemon/store.py:create_pairing_token()` sets the expiry
  timestamp to the current time
- pairing scripts do not present or validate a token during activation
- replay detection is not implemented

Impact:

- the repo has a named trust flow, but not an enforceable trust ceremony
- the stored expiry field is present without providing security value

Recommendation:

- separate issued-at from expires-at
- validate tokens during activation
- add replay and expiry failure paths before claiming pairing robustness

### 5. Medium - Operations inbox routing exists in the spine, but not in the UI

Evidence:

- pairing, Hermes, and rejected control events append to
  `services/home-miner-daemon/state/event-spine.jsonl`
- `services/home-miner-daemon/cli.py events` can read those events back
- `apps/zend-home-gateway/index.html` shows static inbox empty states and does
  not fetch spine events

Impact:

- the repository proves event append
- it does not yet prove a user-facing inbox projection fed by the spine

Recommendation:

- add a query path for inbox-visible events and render them by `eventId`
- keep the reviewed contract rule that inbox items derive from spine events,
  not from a separate handcrafted receipt list

### 6. Medium - Shell wrappers hide rejected control details

Evidence:

- `scripts/set_mining_mode.sh` runs with `set -e`
- when `python3 cli.py control ...` exits non-zero, the shell wrapper exits
  before echoing structured JSON back to the operator
- the review run produced a rejected `control_receipt` event even when the
  wrapper surfaced no useful failure text

Impact:

- operator proof transcripts are weaker than the underlying CLI behavior
- debugging authorization or daemon failures is harder than necessary

Recommendation:

- capture and print structured CLI output before exiting
- make control denial a first-class proof path, not an accidental silent failure

## What The Slice Already Proves

- Shared identity exists in code today: pairings and spine events both reference
  one principal id.
- Capability-scoped pairing exists in code today: `observe`-only clients are
  rejected at the CLI control path, while `observe,control` pairings are stored
  distinctly.
- The event spine already unifies pairing events, control receipts, and Hermes
  summaries in one append-only journal.

These are real gains. They are enough to justify a reviewed contract and to
start implementation against a stable boundary.

## Validation Notes

Successful local checks in this review environment:

- `./scripts/pair_gateway_client.sh --client control-phone --capabilities observe,control`
  created a pairing record and appended pairing events
- `./scripts/pair_gateway_client.sh --client observe-phone --capabilities observe`
  created an observe-only pairing
- `python3 cli.py control --client observe-phone --action set_mode --mode balanced`
  returned `unauthorized`
- `./scripts/hermes_summary_smoke.sh --client control-phone`
  appended a Hermes summary into the same event spine

Validation that could not be completed here:

- `./scripts/bootstrap_home_miner.sh` could not bind `127.0.0.1:8080` in this
  sandboxed environment and failed with `PermissionError: [Errno 1] Operation not permitted`
- because of that sandbox restriction, live HTTP status and control flows were
  reviewed by code inspection rather than a full daemon-backed proof

## Recommended Next Slice

The next implementation pass should stay narrow:

1. Unify the state root for daemon, pairings, and spine.
2. Enforce `observe` on every read path, not just `control` on writes.
3. Replace plaintext spine payloads with encrypted payloads or encrypted
   pointers.
4. Render the inbox from spine events so the user-facing product matches the
   contract.

That would turn this from a promising reviewed boundary into a truly honest
milestone 1 proof.
