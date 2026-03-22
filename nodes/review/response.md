I now have a complete picture. Here's the review.

---

# Documentation & Onboarding — Review

## Verdict: **CONDITIONAL PASS — 3 blockers, 5 warnings**

The documentation set is structurally complete and well-organized. Five documents exist, the README is under 200 lines (135), and the writing quality is solid. However, the self-review is inflated — it claims "all quickstart commands work" when they demonstrably don't, and several claims in the docs contradict the source code.

---

## Blockers (must fix before merge)

### B1. Quickstart is broken: bootstrap grants `observe` only, step 5 requires `control`

`cli.py:78` — `cmd_bootstrap` pairs with `['observe']` only:
```python
pairing = pair_client(args.device, ['observe'])
```

But README quickstart step 5 runs:
```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

`cli.py:134` checks `has_capability(args.client, 'control')` and will return `unauthorized`. **The quickstart fails on its own happy path.**

The review document (`review.md:131-133`) claims this was tested and works. It was not.

**Fix:** Either bootstrap with `['observe', 'control']` or change quickstart step 5 to a `status` command (observe-only). The operator quickstart has the same issue — it bootstraps then tries to control.

### B2. Operator quickstart tells operators to edit source code

`docs/operator-quickstart.md:166-183` "Option C" tells operators to modify `daemon.py` to add HTML serving. This breaks the update path (next `git pull` will conflict) and is inappropriate for a quickstart guide. This should be removed or replaced with a reverse proxy example.

### B3. Architecture doc claims JSONL is "crash-safe (append is atomic at line boundaries)"

`docs/architecture.md:369` — This is false. Python's `f.write(data + '\n')` (`spine.py:64-65`) is NOT atomic. A crash during write can leave a partial JSON line, corrupting the tail of the spine. Additionally, `spine.py` uses `open(file, 'a')` without any file lock, and the daemon is threaded (`ThreadedHTTPServer`), so concurrent event appends can interleave writes. The doc should say "append-only by convention; crash recovery not guaranteed in milestone 1."

---

## Security Review (Nemesis Passes)

### Pass 1 — First-Principles: Trust Boundaries

**S1. Daemon API has zero authentication.** The docs repeatedly say "capability check is done by CLI" (`docs/api-reference.md:58,101,141,182`), which frames this as a design choice. But the consequence is undersold: when the operator quickstart tells users to set `ZEND_BIND_HOST=0.0.0.0`, ANY device on the LAN can `curl -X POST /miner/stop` without going through CLI capability checks. The HTML UI also makes direct HTTP calls, bypassing capabilities entirely. The docs should explicitly state: "The HTTP API is unauthenticated. Capability checks exist only in the CLI. Any HTTP client on the network can control the miner."

**S2. Pairing tokens are dead code.** `store.py:86-90` — `create_pairing_token()` sets `token_expires_at` to `datetime.now()` (immediately expired) and `token_used` is stored but never read. The docs describe pairing as if it provides access control, but it's purely advisory metadata. This should be documented as "pairing records metadata only — no enforcement in milestone 1."

**S3. PID file race.** `bootstrap_home_miner.sh:62-68` checks PID file, then starts daemon. Between the check and the write, another invocation could start. Also `kill -9` after only 1 second of `kill` is aggressive — if the spine is mid-write, the JSONL can be truncated.

### Pass 2 — Coupled-State Consistency

**S4. Pairing store and spine can diverge.** `cli.py:73-93` (`cmd_bootstrap`) writes to the pairing store first, then appends `pairing_granted` to the spine — but skips `pairing_requested`. `cli.py:98-128` (`cmd_pair`) writes to the store first, then appends both spine events. If the process crashes between the store write and the spine write, the store has a pairing record with no corresponding spine event. The spine is documented as "source of truth" but can fall behind the store.

**S5. Concurrent spine writes in threaded server.** `spine.py:64-65` appends with `open(file, 'a')` and no lock. `daemon.py:210` uses `ThreadingMixIn`, so concurrent requests can interleave partial writes. This contradicts the architecture doc's claim of crash safety and ordered events.

### Assessment

For a **milestone 1 LAN-only simulator**, these are acceptable engineering tradeoffs. But the documentation should be honest about them rather than framing pairing as access control and JSONL as crash-safe. The current docs would give an operator false confidence about the security posture.

---

## Warnings (should fix)

### W1. Observability drift

`docs/architecture.md:460-482` lists metrics and log events that don't match `references/observability.md`:
- Metric names missing `gateway_` prefix: `pairing_attempts_total` vs `gateway_pairing_attempts_total`
- `gateway.bootstrap.complete` in arch doc but not in reference (reference has `gateway.bootstrap.failed`)
- Arch doc missing several reference events: `gateway.inbox.appended`, `gateway.inbox.append_failed`, `gateway.hermes.summary_appended`, `gateway.hermes.unauthorized`

### W2. README directory structure is incomplete

- Missing `scripts/fetch_upstreams.sh`
- Missing `references/design-checklist.md` and `references/observability.md`

### W3. `ZEND_TOKEN_TTL_HOURS` documented but unused

`docs/operator-quickstart.md:38` lists `ZEND_TOKEN_TTL_HOURS` as a config variable, but it doesn't appear anywhere in the codebase. This is phantom documentation.

### W4. Contributor guide recommends pytest coverage but no coverage config

`docs/contributor-guide.md:157` suggests `--cov=services/home-miner-daemon` but there's no `.coveragerc` or pytest coverage plugin (`pytest-cov`) configured. Since the project is stdlib-only, `pytest-cov` is an external dependency that may not be installed.

### W5. Self-review inflated

`review.md` marks every acceptance criterion as passing and claims end-to-end testing. The quickstart capability bug (B1) would have been caught by actually running the commands in sequence. The review should be marked as "not independently verified."

---

## Correctness Summary

| Claim | Verified | Status |
|-------|----------|--------|
| README under 200 lines | 135 lines | PASS |
| Quickstart works end-to-end | Fails at step 5 (unauthorized) | **FAIL** |
| API curl examples match code | Endpoints and responses match | PASS |
| Architecture matches modules | Module descriptions accurate | PASS |
| Event kinds documented correctly | All 7 kinds match spine.py | PASS |
| Self-contained (no broken links) | All cross-references valid | PASS |
| Metrics/observability accurate | Diverges from reference | **WARN** |
| JSONL crash-safe | Not true in Python | **FAIL** |

## Milestone Fit

The documentation lane delivers the right artifacts for a milestone 1 onboarding package. The gap is correctness, not coverage. Fix B1-B3, and this is ready to merge.