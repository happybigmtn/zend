Now I have full context. Let me write the review.

---

## CI/CD Pipeline Lane — Review

**Pipeline status on current codebase: FAILS** — not green.

### Correctness Assessment

#### CRITICAL: Pipeline fails on current codebase

The test job (`.github/workflows/ci.yml:24-31`) runs `pytest` twice — once without coverage (line 24), once with (lines 27-31). Since **zero test files exist** in the repository, both invocations collect 0 items. The coverage step then fails because `0% < 80%` (`--cov-fail-under=80`), producing exit code 1. The pipeline as written cannot pass.

**Remedy**: Either (a) add real tests, or (b) remove the `fail-under=80` guard until coverage exists. The spec correctly notes tests are missing — but the workflow was generated with the threshold anyway, guaranteeing a red pipeline.

#### CRITICAL: `bandit` missing from pip install

The test job installs `pytest pytest-cov`. The lint job installs `ruff`. The security job installs `bandit`. These are three separate jobs with no shared dependency caching, which is fine — but the spec (`spec.md:63`) says bandit is installed in the security job, and it is (line 62-63). So this is actually correct. However, **the security job references `scripts/no_local_hashing_audit.sh` which does not use `--client apps/zend-home-gateway/index.html`** — the `--client` arg is consumed as metadata only (line 41: `echo "Running local hashing audit for: $CLIENT"`), not as a path to audit. The script hard-codes its audit target to `$DAEMON_DIR` (line 57). This is misleading but not broken.

#### No ruff configuration file

The lint job runs `ruff check` and `ruff format --check` with zero config — no `pyproject.toml`, no `.ruff.toml`, no `ruff.toml`. Ruff's defaults are reasonable, but this means: no custom rule sets, no ignored paths for `__pycache__` or generated files, no line-length override. Works for now, but fragile if the repo grows.

### Milestone Fit

| Required artifact | Status | Notes |
|---|---|---|
| GitHub Actions workflow | ✅ Done | `.github/workflows/ci.yml` valid YAML |
| Python tests step | ⚠️ Broken | No tests exist — coverage gate fails |
| Linting (ruff) step | ✅ Passes | `ruff check` + `ruff format --check` both green |
| Security scan (bandit) | ✅ Passes | `bandit -ll` reports 0 issues |
| No-hashing audit step | ⚠️ Stub | Passes trivially — see §Security |
| Branch protection | ⚠️ Deferred | Correctly noted as manual step |

`outputs/ci-cd-pipeline/spec.md` exists and is accurate about the implementation. `outputs/ci-cd-pipeline/review.md` does **not exist** — the lane completed without writing it.

### Remaining Blockers

1. **Zero test coverage** — The `--cov-fail-under=80` guard will never pass until tests exist. This is the single blocker to a green pipeline.
2. **No review artifact** — `outputs/ci-cd-pipeline/review.md` was listed as a durable artifact but was never written.
3. **Branch protection** — Requires manual GitHub UI or `gh` CLI; cannot be done via file-only CI.

---

### Nemesis-Style Security Review

#### Pass 1 — First-Principles Challenge

**Trust boundaries and authority:**

- `daemon.py` binds to `ZEND_BIND_HOST` (default `127.0.0.1`) and `ZEND_PORT` (default `8080`). In production (LAN mode), this binds to a LAN interface — any device on the same network can call `/miner/start`, `/miner/stop`, `/miner/set_mode`, and read `/status`. **No authentication on any HTTP endpoint.** The `cli.py` capability checks (`has_capability`) are CLI-side only; they never hit the daemon. A `curl` from any LAN host controls the miner. This is a deliberate design choice for milestone 1, but it means the security job's bandit scan gives a false confidence signal — bandit checks for code-level issues, not protocol-level ones.

- `store.py:68` writes `principal.json` and `PAIRING_FILE` without `atomic` write (no `os.rename` over a temp file). Concurrent writes from multiple CLI invocations can corrupt JSON. This is unlikely in normal use but exploitable.

- `spine.py:65` appends to `event-spine.jsonl` with a bare `open(... "a")` — not atomic under concurrent writers.

**Operator safety / dangerous actions:**

- The `control` command issues `POST /miner/start` and `POST /miner/stop` to the daemon. These are idempotent at the simulator level (`already_running`/`already_stopped` returns). Good. But `POST /miner/set_mode` is not idempotent — calling it twice with different modes produces two state transitions. No idempotency key. Acceptable for a simulator.

**Privilege escalation paths:**

- `has_capability` (store.py:133) is checked in CLI commands. But `load_or_create_principal` is called *before* the capability check in `cmd_control` (cli.py:161 vs 148). This means an unpaired device gets a principal created, then gets told it lacks capability. The principal file is side-effect-only, but it means an attacker can force-creation of principals for every device they probe.

#### Pass 2 — Coupled-State Review

**Token lifecycle is half-implemented:**

`store.py` defines `token_expires_at` (line 50) and `token_used` (line 51) on `GatewayPairing`. Neither field is ever checked anywhere in the codebase. A pairing token that was marked as used still grants capabilities. An expired token still grants capabilities. This is dead code that could mislead future developers into thinking token enforcement exists.

**Pairing state vs. capability state:**

`get_pairing_by_device` (store.py:124) does a linear scan of all pairings. In the current design, each device has one pairing (enforced by `pair_client` raising on duplicate device names). But `has_capability` relies on this invariant — if a future version allows re-pairing, the linear scan returns the first match and could return a stale pairing.

**Spine event consistency:**

`append_pairing_granted` and `append_pairing_requested` are called in `cmd_pair` (cli.py:121-124), but the spine write is **not inside the same atomic transaction as the pairing store write** (store.py:118-119). If the spine write fails after the store write succeeds, the pairing exists but no event was recorded. Conversely, if the spine write succeeds but the store write fails, the event exists for a pairing that doesn't. The spec says "The event spine is the source of truth" — but the store is written first, creating an inconsistency window.

**The no-hashing audit is theater:**

`no_local_hashing_audit.sh` line 60 uses:
```bash
grep -r "hash" "$DAEMON_DIR"/*.py 2>/dev/null | grep -v "hashrate" | grep -v "#" | grep -q "def.*hash"
```
This grep pattern is trivially evaded — `def get_hash(self)` would be caught, but `def compute(self): # sha256` would not (the `#` filter is too broad). More importantly, the script never actually inspects `apps/zend-home-gateway/index.html` despite receiving it as `--client`. The `--client` argument is consumed as a string and printed, nothing more. The script does not audit the gateway client at all.

### Summary

| Category | Finding | Severity |
|---|---|---|
| Pipeline | Coverage gate fails (0 tests) | **Critical** |
| Pipeline | Review artifact missing | Medium |
| Security | No daemon auth — LAN-exposed endpoints | Known design, not a bug |
| Security | Token expiration dead code | Low (unused feature) |
| Security | Non-atomic JSON/JSONL writes | Low (concurrency window) |
| Security | No-hashing audit is a stub | Medium (false confidence) |
| Security | Spine/store write ordering inconsistency | Low (no atomicity) |

The pipeline infrastructure is structurally sound. The single blocker is the absence of tests — which is a codebase gap, not a pipeline gap. Everything that *can* be automated has been automated correctly in the YAML.

`★ Insight ─────────────────────────────────────`
1. **No-auth on LAN is a known milestone-1 tradeoff** — bandit and ruff checks are code-level scans and cannot catch protocol-level missing auth. The security scan "passing" is not meaningful for network exposure.
2. **The `--cov-fail-under=80` guard is a landmine** — it was set in the spec before tests existed. A better pattern: set `fail-under-minimum` to `0` (always pass) with an explicit TODO comment, then raise the threshold only when tests are added. This prevents a pipeline that starts red.
`─────────────────────────────────────────────────`