Now I have the full picture. Here's the review.

---

# CI/CD Pipeline Lane Review

## Verdict: **BLOCK — pipeline will not run green**

The review document claims "Verify pipeline runs green on current codebase" is checked off. This is false. The test job will fail in CI.

---

## P0: Pipeline does not pass (blocking)

### Test job fails on zero tests

`pytest` exits with code 5 ("no tests collected"), which is a non-zero exit — the `test` step fails. The coverage step (`--cov-fail-under=80`) compounds the failure since 0 tests = 0% coverage. The review even acknowledges this at the bottom ("The test job will report 'no tests collected'") but simultaneously checks off "Verify pipeline runs green."

**Fix options** (pick one):
1. Remove the test job entirely and re-add it when tests exist (honest)
2. Add `--no-header -q || true` to suppress the pytest failure (dishonest — defeats the purpose)
3. Change the test step to `python3 -m pytest services/home-miner-daemon/ -v --tb=short || echo "No tests yet"` — but this swallows real test failures too

The honest fix is to split the test step from coverage, and gate the coverage step on tests existing. Or just remove the test job and note it as pending plan 004.

### Double pytest run is wasteful

The workflow runs pytest twice — once for tests, once for coverage. These should be a single step:
```yaml
run: python3 -m pytest services/home-miner-daemon/ -v --tb=short --cov=services/home-miner-daemon --cov-report=term-missing --cov-fail-under=80
```

---

## P1: Security review (Nemesis pass)

### Pass 1 — Trust boundaries and authority assumptions

**`ZEND_DAEMON_URL` env var makes `# nosec: B310` a lie.**

The `nosec: B310` suppression on `cli.py:46` is justified as "the URL is constructed from `DAEMON_URL`, which defaults to `http://127.0.0.1:8080`." But `DAEMON_URL` is set from `os.environ.get("ZEND_DAEMON_URL", ...)`. An attacker who controls the environment can set `ZEND_DAEMON_URL=file:///etc/shadow` or `ZEND_DAEMON_URL=ftp://evil.example.com` and `urlopen` will happily follow. The nosec suppression is only valid if the URL scheme is validated first.

The bandit scan passes now, but the underlying vulnerability remains. The CI gives a false green for security on this file.

**Daemon HTTP endpoints have zero authentication.**

Anyone on `127.0.0.1` can `POST /miner/start`, `/miner/stop`, `/miner/set_mode`. The CLI checks `has_capability` before forwarding, but nothing stops a direct `curl` to the daemon. This is explicitly a milestone-1 simulator, but the CI pipeline's security scan doesn't flag it because bandit doesn't know about HTTP auth. Worth noting as a known gap.

**No-hashing audit is security theater.**

`scripts/no_local_hashing_audit.sh` accepts `--client apps/zend-home-gateway/index.html` but never actually inspects that file. It greps the daemon Python code for `def.*hash`. The argument name suggests it should audit the *client*, but it audits the *server*. The grep pattern is also trivially bypassable (e.g., `exec(b64decode(...))` would be invisible to it).

For CI, this check provides a false sense of assurance. It's a grep wrapper dressed as an audit.

### Pass 2 — Coupled state and mutation paths

**`create_pairing_token()` creates immediately-expired tokens.**

`store.py:91`: `expires = datetime.now(timezone.utc).isoformat()` — the token expires at the moment of creation. Every pairing is born expired. The CI pipeline doesn't catch this because there are no tests and bandit doesn't check logic bugs.

**State file corruption on concurrent writes.**

`store.py` uses `json.load`/`json.dump` without file locking. Two concurrent `pair_client` calls can race: both read the same pairings dict, both write, one loses. The spine uses append mode (`"a"`) which is somewhat safer but still not atomic on all filesystems. Again, not a CI issue per se, but the CI doesn't protect against this since there are no tests.

**`principal` created before validation in `cmd_control`.**

`cli.py:162`: `load_or_create_principal()` is called before `get_pairing_by_device(args.client)`. If the device isn't paired, the principal is still created as a side effect. The `has_capability` check at line 149 already gates on pairing, so this is a minor ordering issue, but it means the first `control` attempt by an unpaired device creates a principal file unnecessarily.

---

## P2: Spec/Review document quality

### Review self-contradicts on bandit results

The "Local Verification Results" section shows `Total issues (by severity): Medium: 1` but the "Bandit Findings" section says `Medium: 0 / No issues identified`. These are pre-fix and post-fix outputs mixed together. The verification section should show post-fix results.

### Missing `requirements.txt` or `pyproject.toml`

The CI installs `pip install pytest pytest-cov`, `pip install ruff`, `pip install bandit` without pinned versions. This means CI behavior drifts over time as package versions change. The project has no dependency manifest at all.

### No pip caching

Each CI run downloads and installs ruff/bandit/pytest from scratch. Adding `actions/setup-python@v5` with `cache: 'pip'` and a requirements file would cut ~10-20s per job.

---

## P3: Minor / style

- `ci.yml:20`: Python version `"3.12"` is hardcoded. The codebase has no `.python-version` or `pyproject.toml` constraint. Fine for now, but fragile.
- The workflow name is `CI` but the spec calls the security job "No-hashing audit" while the step name is just "No-hashing audit." Consistency is fine.
- Branch protection instructions are clear and actionable. This is a post-merge manual step, correctly noted as pending.

---

## Summary table

| Finding | Severity | Blocking? |
|---------|----------|-----------|
| Test job fails (no tests, 0% coverage) | P0 | **Yes** |
| Double pytest invocation | P1 | No |
| `nosec: B310` suppression invalid (env-controlled URL) | P1 | No, but false green |
| No-hashing audit doesn't inspect its `--client` argument | P1 | No, but false assurance |
| Review doc self-contradicts on bandit results | P2 | No |
| Pairing tokens expire at creation | P2 | No (logic bug, not CI) |
| No dependency pinning | P2 | No |
| No pip caching | P3 | No |

---

## Recommended path forward

1. **Remove the test+coverage job** from the workflow (or gate it with a test-file existence check). Re-add when plan 004 delivers tests. Mark the task honestly as "pending tests."
2. **Validate URL scheme** in `daemon_call` before `urlopen` — restrict to `http://` only. Then the `nosec` is honest.
3. **Fix the review document** — replace the pre-fix bandit output with post-fix output.
4. **Decide on the no-hashing audit** — either make it actually inspect the `--client` file path, or rename it to clarify what it actually checks.

`★ Insight ─────────────────────────────────────`
- **pytest exit code 5** means "no tests collected" — it's a non-zero exit distinct from test failure (code 1). Many CI pipelines silently fail on this because people assume "no output = pass." Always check what exit code your test runner uses for the "no tests" case.
- **`# nosec` annotations are claims, not proofs.** They tell bandit to skip a line, but the underlying risk assessment must be re-evaluated whenever the inputs change. Here the input (`DAEMON_URL`) is environment-controlled, invalidating the original rationale.
- **Append-mode file writes** (`open(f, "a")`) are not atomic on all filesystems. On Linux with ext4, small writes (< 4096 bytes) to append-only files are typically atomic, but this is a filesystem implementation detail, not a POSIX guarantee. For a JSONL event spine, this is usually fine in practice but not contractually safe.
`─────────────────────────────────────────────────`