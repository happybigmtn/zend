I've now read all source files, contracts, and documentation. Here's my review.

---

# Documentation & Onboarding Lane — Review

## Verdict: CONDITIONAL PASS — 2 code bugs, 1 doc inaccuracy, and security notes

The documentation is high quality — well-structured, accurate against most of the running code, and honest about scope. The self-review (review.md) caught and fixed the enum serialization bug, which is good practice. But I found issues the self-review missed.

`★ Insight ─────────────────────────────────────`
The "specify" stage produced a remarkably thorough MiniMax output for 470 tokens — the spec is well-bounded. But the review.md's verification was shallow in one critical path: event filtering was tested only with `--kind all`, which masks a crash on any other kind value.
`─────────────────────────────────────────────────`

---

## Pass 1 — Correctness

### BUG 1: `cmd_events` kind filter crashes (Code, not docs)

`cli.py:190-191` passes a raw string to `spine.get_events(kind=kind)`, but `spine.py:87` calls `kind.value` on it — plain strings don't have `.value`.

```python
# cli.py:190
kind = args.kind if args.kind != 'all' else None
events = spine.get_events(kind=kind, limit=args.limit)

# spine.py:87
events = [e for e in events if e.kind == kind.value]  # AttributeError
```

The documented example `--kind control_receipt` in both the API reference and operator quickstart would crash. The review.md only tested `--kind all` (which sets kind=None and skips the filter).

**Severity:** Medium — documented CLI usage path crashes.

### BUG 2: Bootstrap is not idempotent

`bootstrap_home_miner.sh` calls `stop_daemon` then `start_daemon` then `bootstrap_principal`. The stop/start cycle does NOT wipe `state/`, so if `state/pairing-store.json` already contains `alice-phone`, `cmd_bootstrap` → `pair_client('alice-phone', ...)` raises `ValueError("Device 'alice-phone' already paired")`.

The contributor guide claims "All scripts are idempotent" (`docs/contributor-guide.md:103`). This is false for bootstrap.

**Severity:** Medium — operator re-running bootstrap gets an error instead of a clean restart.

### INACCURACY 1: CORS blocks the documented deployment path

The operator quickstart (`docs/operator-quickstart.md:185-191`) tells operators to serve `index.html` on port 8081 and the daemon on 8080. The gateway client makes `fetch()` calls to the daemon. This is a cross-origin request — `http://192.168.1.100:8081` → `http://192.168.1.100:8080` — and the daemon sets no CORS headers. The browser will block these requests.

**Severity:** Medium — following the documented operator path produces a non-functional UI.

### Minor Issues

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| 3 | `/health` `uptime_seconds` always 0 — value only updates inside `get_snapshot()`, but `health` property reads stale field | `daemon.py:82-86` | Low |
| 4 | `ZEND_TOKEN_TTL_HOURS` documented in operator quickstart but no code reads it | `operator-quickstart.md:65` | Low |
| 5 | `token_expires_at` is set to `datetime.now()` (creation time) — not a future time | `store.py:88-89` | Low |
| 6 | `pairing_granted` payload omits `pairing_token` field required by contract | `spine.py:107-116` vs `references/event-spine.md:50-51` | Low |
| 7 | README auth column says `/status` requires `observe` — daemon doesn't enforce it, only CLI does | `README.md:90` | Low (technically true but misleading) |

---

## Pass 2 — Nemesis Security Review

### Trust Boundaries & Authority

**CRITICAL (deferred by design, but must be documented more prominently):** The capability model is cooperative only. The daemon has zero authentication. Any process that can reach the HTTP port can start/stop mining, regardless of pairing state.

The gateway client (`index.html`) calls the daemon directly — it does not go through the CLI. So the "capability check" in the CLI is completely bypassed by the primary user-facing client. This means:

- Any device on the LAN can issue `POST /miner/start` or `POST /miner/set_mode`
- The pairing system provides zero security in milestone 1 — it's only a CLI-side UX guardrail
- The architecture doc acknowledges this at `architecture.md:273-276`, but the operator quickstart's security notes (`operator-quickstart.md:370-381`) could give a false sense of protection by mentioning "capability scoping handles authorization"

**Recommendation:** Add a clear callout in operator-quickstart.md security notes: "In milestone 1, any device on your LAN can control the miner directly via HTTP. The capability model is enforced only by the CLI, not the daemon."

### Coupled-State Consistency

**Pairing store vs event spine can diverge.** In `cli.py:102-115`, `pair_client()` writes to `pairing-store.json`, then `append_pairing_requested()` and `append_pairing_granted()` write to the spine. If the process crashes between the store write and the spine writes, the pairing exists but has no audit trail.

Similarly, `cmd_bootstrap` (`cli.py:73-95`) creates the principal and pairing, then appends a pairing_granted event. Crash between these steps leaves the system in an inconsistent state.

**Severity:** Low for milestone 1 (simulator, home use). Will need addressing before production.

### Concurrency Safety of Spine Appends

`spine.py:64` opens the file in append mode with no lock:

```python
def _save_event(event: SpineEvent):
    with open(SPINE_FILE, 'a') as f:
        f.write(json.dumps(asdict(event)) + '\n')
```

The daemon uses `ThreadingMixIn`, so concurrent POST requests could interleave mid-write if the JSON line exceeds `PIPE_BUF` (4096 bytes on Linux). The architecture doc claims "JSONL appends atomically with a single `open(..., 'a')` call" — this is only true for short writes and doesn't account for multi-threaded Python.

**Severity:** Low now (single-user simulator), but the architecture doc's atomicity claim at `architecture.md:311-314` overstates the guarantee.

### Service Lifecycle

- **PID file race:** `bootstrap_home_miner.sh:62-69` checks PID file then starts daemon — another process could bind port 8080 between the check and start. Low risk for home use.
- **State file permissions:** `os.makedirs(STATE_DIR, exist_ok=True)` creates with default umask. On a shared machine, other users could read `principal.json` and `pairing-store.json`. Low risk if the machine is single-user.
- **`kill -9` fallback** (`bootstrap_home_miner.sh:54`): The force-kill after 1 second doesn't give the daemon time to clean up. If the daemon held a spine write mid-line, the force-kill could corrupt the last JSONL entry.

---

## Milestone Fit

The documentation scope is well-matched to milestone 1. It correctly describes the simulator-only state, doesn't overreach into future features, and the "What's Not Covered" sections are honest. The lane output is useful — a new contributor can actually get from clone to running system using these docs (modulo the CORS and bootstrap idempotency issues).

---

## Remaining Blockers Before Merge

| Priority | Item | Effort |
|----------|------|--------|
| **Must fix** | BUG 1: `spine.get_events` kind filter crashes on string input | 1-line fix |
| **Must fix** | BUG 2: Bootstrap not idempotent OR remove "idempotent" claim | 5-line fix |
| **Must fix** | CORS: Either add CORS headers to daemon OR fix operator-quickstart to not recommend cross-origin serving | 10-line fix |
| **Should fix** | Security note: explicitly state daemon has no auth, capabilities are CLI-only | 2-sentence addition |
| **Nice to have** | Fix `/health` uptime to compute from `_started_at` directly | 3-line fix |
| **Nice to have** | Remove `ZEND_TOKEN_TTL_HOURS` from docs until implemented | 1-line removal |

`★ Insight ─────────────────────────────────────`
The pattern here is instructive: the self-review (review.md) verified the **happy path** thoroughly — every endpoint, every script, every CLI command. But it tested events only with `--kind all`, tested bootstrap only on a fresh state directory, and didn't test the documented cross-origin deployment. Real bugs live at boundary conditions and state transitions, not on the golden path.
`─────────────────────────────────────────────────`

---

## Review Quality Assessment

The existing review.md is thorough for what it covers — endpoint verification, enum fix, CLI testing. It caught a real code bug (enum serialization) during verification. The quality checklist is good practice. The review missed the three must-fix items above because it didn't test the event kind filter path, didn't test bootstrap re-runs, and didn't test the gateway client from a different origin.