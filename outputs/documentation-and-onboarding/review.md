# Documentation & Onboarding — Review

**Status:** FAILED
**Date:** 2026-03-22
**Reviewer:** claude-opus-4-6 (nemesis review)
**Lane:** documentation-and-onboarding

## Verdict

The lane produced 5 documentation artifacts with good structure and readability. However, the self-verification is unreliable: 3 of 8 documented API endpoints do not exist in the daemon, an environment variable is fabricated, the contributor guide's examples will fail at runtime, and the security model described in the architecture doc misrepresents where authorization actually happens. The review.md that shipped with this lane marked all items as "Verified ✓" without executing a single curl command against a running daemon.

**Blocking issues must be fixed before this lane can be accepted.**

---

## Pass 1 — Correctness

### BLOCKER C1: Three phantom HTTP endpoints

The API reference (`docs/api-reference.md`) documents 8 endpoints. Only 5 exist in `daemon.py`:

| Endpoint | In daemon.py? | What actually happens |
|----------|---------------|----------------------|
| `GET /health` | Yes | `GatewayHandler.do_GET` line 169 |
| `GET /status` | Yes | `GatewayHandler.do_GET` line 172 |
| `POST /miner/start` | Yes | `GatewayHandler.do_POST` line 186 |
| `POST /miner/stop` | Yes | `GatewayHandler.do_POST` line 189 |
| `POST /miner/set_mode` | Yes | `GatewayHandler.do_POST` line 192 |
| **`GET /spine/events`** | **NO** | Returns `404 {"error": "not_found"}` |
| **`GET /metrics`** | **NO** | Returns `404 {"error": "not_found"}` |
| **`POST /pairing/refresh`** | **NO** | Returns `404 {"error": "not_found"}` |

The prior review.md attributed `/spine/events` to "via get_events function" and `/pairing/refresh` to "via pair_client function." These functions exist in `spine.py` and `store.py` respectively, but **they are not wired to HTTP routes**. The CLI calls them as Python imports, not via HTTP. Every curl example for these 3 endpoints will return a 404.

**Fix:** Either remove the phantom endpoints from the API reference, or implement the HTTP routes in `daemon.py`.

### BLOCKER C2: Contributor guide examples will fail at runtime

The bootstrap command (`cli.py bootstrap --device alice-phone`) grants only `['observe']` capability (cli.py:78). The contributor guide then shows control commands using `alice-phone`:

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

This will return `{"success": false, "error": "unauthorized", "message": "This device lacks 'control' capability"}` because `alice-phone` only has `observe`.

**Fix:** Either change bootstrap to grant `['observe', 'control']`, or use a different device name in the control examples that has been paired with control capability.

### BLOCKER C3: Fabricated environment variable

The operator quickstart documents `ZEND_TOKEN_TTL_HOURS` (default: 24) in the configuration table. This environment variable does not exist anywhere in the codebase. Grep for `TOKEN_TTL` returns zero hits.

**Fix:** Remove `ZEND_TOKEN_TTL_HOURS` from the configuration table, or implement it.

### C4: No test files exist

The README and contributor guide both instruct users to run:
```bash
python3 -m pytest services/home-miner-daemon/ -v
```

There are zero `test_*.py` files in `services/home-miner-daemon/`. This command will either find no tests (if pytest is installed) or fail (if not). The spec's verification criterion says "A contributor... can run the test suite by following only this document" — there is no test suite.

**Fix:** Either create tests or remove the test instructions and note that tests are not yet implemented.

### C5: Quickstart command 4 will fail

README quickstart step 4:
```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

After bootstrap, only `alice-phone` is paired (with `observe`). `my-phone` does not exist in the pairing store. `has_capability('my-phone', 'observe')` returns `False`. The CLI will print `{"error": "unauthorized"}`.

**Fix:** Either use `--client alice-phone` in the quickstart, or pair `my-phone` in step 2.

### C6: README directory structure incomplete/inaccurate

- Missing from `references/`: `design-checklist.md`, `hermes-adapter.md`, `observability.md`
- Missing from `scripts/`: `fetch_upstreams.sh`
- The listing is selective but doesn't indicate that — reader assumes it's exhaustive

### C7: Architecture doc omits `token_used` field

The `GatewayPairing` dataclass shown in `docs/architecture.md:320-327` omits the `token_used: bool` field that exists in `store.py:49`.

### C8: Token expiry logic is broken (docs mask this)

`create_pairing_token()` in `store.py:86-90` sets `expires = datetime.now(timezone.utc).isoformat()` — the token expires the instant it's created. But `has_capability()` never checks expiry. The docs present token expiry as a feature (`ZEND_TOKEN_TTL_HOURS`, `token_expires_at` in responses) but it's dead code.

---

## Pass 2 — Nemesis Security Review

### S1: CRITICAL — Authorization is cosmetic; HTTP API is completely open

**Trust boundary violation.** The daemon's HTTP API (`daemon.py`) performs **zero authorization checks**. Any client on the LAN can:

```bash
curl -X POST http://<daemon-ip>:8080/miner/start      # Start mining
curl -X POST http://<daemon-ip>:8080/miner/stop        # Stop mining
curl -X POST http://<daemon-ip>:8080/miner/set_mode \
  -d '{"mode":"performance"}'                            # Max hash rate
```

Capability checks (`has_capability`) only exist in `cli.py`. The architecture doc draws an authorization flow diagram (lines 330-352) implying the daemon checks capabilities — **it does not**. The `index.html` command center confirms this: it calls `fetch('/miner/set_mode', ...)` directly without any authentication token or device identity.

**Impact:** Any device on the LAN controls the miner. The entire pairing/capability system is security theater — it only gates the CLI, not the actual control surface.

**The docs describe this honestly in one place** (api-reference.md:369 "The current implementation does not enforce per-request authentication") **but contradict it in another** (architecture.md authorization flow diagram). A reader of the architecture doc will believe authorization is enforced.

### S2: Coupled-state inconsistency — Spine writes are not atomic

`_save_event()` in `spine.py:63-65` opens the JSONL file in append mode without file locking. The daemon uses `ThreadedHTTPServer` (concurrent request handling). Two concurrent control commands could interleave partial JSON lines in `event-spine.jsonl`, corrupting the journal.

Same issue with `save_pairings()` in `store.py:80-83`: `json.dump()` to `pairing-store.json` without locking. Two concurrent `pair_client` calls corrupt the pairing store.

**Impact:** State corruption under concurrent access. The docs don't mention this limitation.

### S3: Bootstrap stop is destructive — SIGKILL after 1 second

`stop_daemon()` in `bootstrap_home_miner.sh:46-58` sends SIGTERM, sleeps 1 second, then unconditionally sends SIGKILL. If the daemon is mid-write to spine or pairing store when SIGKILL arrives, the files are corrupted. The recovery docs say "clear state and re-bootstrap" but don't explain this is a consequence of normal shutdown.

### S4: No request size limits

`daemon.py:177` reads `Content-Length` bytes from the request body without any upper bound. A malicious LAN client can exhaust daemon memory with a single POST.

### S5: Idempotence gaps

- `pair_client()` raises `ValueError` on duplicate device names but doesn't check whether the existing pairing has the same capabilities. Re-pairing a device requires deleting state first.
- `bootstrap_home_miner.sh` calls `stop_daemon` then `start_daemon` then `bootstrap_principal` on every invocation. The second run will fail on `pair_client` because `alice-phone` already exists.

### S6: PID file TOCTOU

`start_daemon()` checks `kill -0 $PID`, but the process could die between the check and subsequent operations. Minor, but the PID could also be recycled by the OS.

---

## Milestone Fit

The spec required 5 artifacts with specific verification criteria. Assessment:

| Artifact | Structure | Accuracy | Verification Criterion Met? |
|----------|-----------|----------|----------------------------|
| README.md | Good | Quickstart steps 4-5 fail | **No** — quickstart doesn't produce `{"status": "ok"}` |
| contributor-guide.md | Good | Control examples fail | **No** — contributor can't run control commands as documented |
| operator-quickstart.md | Good | Fabricated env var, phantom endpoints | **No** — pairing flow references non-existent HTTP endpoint |
| api-reference.md | Good | 3 phantom endpoints | **No** — curl examples 404 |
| architecture.md | Good | Auth model misrepresented | **Partial** — reader would incorrectly predict auth is enforced at HTTP layer |

---

## Remaining Blockers

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| C1 | BLOCKER | 3 phantom endpoints in API reference | Remove or implement in daemon.py |
| C2 | BLOCKER | Contributor guide control examples fail | Fix bootstrap capabilities or fix examples |
| C3 | BLOCKER | Fabricated `ZEND_TOKEN_TTL_HOURS` | Remove or implement |
| C5 | BLOCKER | Quickstart uses unpaired device name | Fix to use `alice-phone` or pair `my-phone` |
| S1 | SECURITY | HTTP API has zero authorization | Document honestly in architecture.md; don't draw auth flow diagrams for non-existent auth |
| C4 | HIGH | No test files exist but docs say to run tests | Create tests or remove instructions |
| S2 | HIGH | Concurrent writes corrupt spine and pairing store | Add file locking or document limitation |
| S5 | MEDIUM | Bootstrap fails on second run (duplicate device) | Make `pair_client` idempotent |
| C6 | LOW | Directory listing incomplete | Add missing files |
| C7 | LOW | Missing `token_used` field in arch doc | Add field |
| C8 | LOW | Token expiry is dead code | Document or implement |
| S3 | LOW | SIGKILL after 1s on shutdown | Increase grace period or handle gracefully |
| S4 | LOW | No request size limits | Add Content-Length cap |

---

## What Works Well

- README structure and architecture diagrams are clear and well-organized
- The contributor guide's "Common Tasks" section (add endpoint, add event kind) is genuinely useful
- Operator quickstart's systemd unit file is practical and correct
- Design system reference in contributor guide properly defers to DESIGN.md
- The separation of observe/control capabilities is a good design — it just needs to be enforced

## Recommendations

1. **Fix blockers C1-C3, C5** before merging — these cause immediate user failures
2. **Align architecture.md auth description with reality** — either implement HTTP-level auth or document that authorization is CLI-only and the HTTP API is open
3. **Run every curl example against a live daemon** and record actual output — the prior review's "Verified ✓" checkmarks were never executed
4. **Add at least smoke tests** so the test command in docs has something to run
5. **Make bootstrap idempotent** so operators can re-run it safely

---

## Sign-off

Lane is **not accepted**. Four blocking correctness issues and one security misrepresentation must be resolved. The documentation quality is high structurally but factually unreliable in critical places. A user following these docs today will hit errors within the first 5 minutes.
