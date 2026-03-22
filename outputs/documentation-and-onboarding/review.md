# Documentation & Onboarding — Review

Status: **Blocked** (3 must-fix issues prevent the lane from passing acceptance)

## Summary

Reviewed all five documentation artifacts against the actual source code. The documentation is structurally complete — every planned artifact exists, sections match the spec, and the writing is clear. However, code-level verification reveals **3 must-fix bugs** that would cause the README quickstart and operator guide to fail at runtime, plus **4 factual inaccuracies** in response formats and API behavior.

## Artifacts Under Review

| Artifact | Path | Verdict |
|---|---|---|
| README | `README.md` | **Blocked** — quickstart step 5 fails |
| Contributor Guide | `docs/contributor-guide.md` | **Blocked** — no test files exist |
| Operator Quickstart | `docs/operator-quickstart.md` | **Blocked** — localStorage trick doesn't work |
| API Reference | `docs/api-reference.md` | Pass with corrections |
| Architecture | `docs/architecture.md` | Pass with corrections |
| Spec | `outputs/documentation-and-onboarding/spec.md` | Pass |

## Must-Fix Issues (lane blockers)

### MF-1: README quickstart step 5 will fail with `unauthorized`

**Location**: `README.md:23-24`

The bootstrap command (`cli.py bootstrap`) pairs `alice-phone` with only `['observe']` capability (cli.py:78). The README quickstart then tries:

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

The `control` subcommand requires `control` capability (cli.py:134). Alice-phone lacks it. The command prints `{"error": "unauthorized"}` and exits 1.

**Fix options** (pick one):
- A) Change `cli.py:78` to `pair_client(args.device, ['observe', 'control'])` so the bootstrap device gets both capabilities.
- B) Change the README quickstart to use `status` (observe-only) instead of `control`, and move control examples to the contributor guide where pairing with control is shown.

**Recommendation**: Option A. The quickstart should demonstrate the full loop. A device you just bootstrapped should be able to control the miner it's paired with.

### MF-2: No test files exist — contributor guide claims "all tests should pass"

**Location**: `docs/contributor-guide.md:40-43`

```
python3 -m pytest services/home-miner-daemon/ -v
```

The directory `services/home-miner-daemon/` contains no `test_*.py` files. Pytest will report "no tests ran" or exit with code 5 (no tests collected). The contributor guide says "All tests should pass" — this is misleading. A new contributor following the guide would see zero tests and wonder if something is broken.

**Fix**: Add a note: "Tests are not yet written for the daemon. The test command is shown here for the workflow pattern; test coverage is tracked in a future plan."

### MF-3: Operator quickstart `localStorage` trick for gateway URL is fabricated

**Location**: `docs/operator-quickstart.md:199-205`

The guide suggests:
```javascript
localStorage.setItem('zend_daemon_url', 'http://192.168.1.100:8080');
```

But `index.html:632` uses a hardcoded constant:
```javascript
const API_BASE = 'http://127.0.0.1:8080';
```

The HTML never reads `zend_daemon_url` from localStorage. It only uses localStorage for `zend_principal_id` and `zend_device_name` (index.html:781-782). The suggested localStorage trick does nothing.

**Fix**: Remove the localStorage suggestion. Keep only the "edit `const API_BASE` in index.html" approach, which is accurate.

## Factual Inaccuracies (should-fix)

### FA-1: API reference shows wrong response format for `missing_mode` error

**Location**: `docs/api-reference.md:239-245`

Documented:
```json
{"success": false, "error": "missing_mode"}
```

Actual (daemon.py:195):
```json
{"error": "missing_mode"}
```

The `missing_mode` error path in `daemon.py` returns `{"error": "missing_mode"}` directly — no `success` field. Only the `invalid_mode` error goes through `miner.set_mode()` which returns `{"success": false, ...}`.

### FA-2: Architecture doc Python examples would crash

**Location**: `docs/architecture.md:196-198`

```python
events = get_events(kind='control_receipt', limit=10)
```

`get_events()` expects `kind: Optional[EventKind]`, not a plain string. Passing a string triggers `kind.value` (spine.py:87) which raises `AttributeError` because strings have no `.value` attribute.

Same bug exists in `cli.py:191` where the CLI passes a raw string to `get_events()` — this is a code bug, not just a docs bug. The events `--kind` filter is broken at runtime.

### FA-3: README links to nonexistent `specs/event-spine.md`

**Location**: `README.md:122`

```markdown
- [Event Spine](specs/event-spine.md) — Append-only encrypted journal
```

Only `specs/2026-03-19-zend-product-spec.md` exists in `specs/`. The `event-spine.md` link is a dead link.

### FA-4: Operator quickstart CORS omission

**Location**: `docs/operator-quickstart.md:186-191`

The guide suggests serving index.html on port 8081 via `python3 -m http.server 8081`, then fetching from the daemon on port 8080. The daemon sets no CORS headers. Browsers will block cross-origin fetch requests from `http://192.168.1.100:8081` to `http://192.168.1.100:8080`.

The workaround (editing `API_BASE` and opening the file directly) avoids this, but the `python3 -m http.server` suggestion will silently fail in the browser console.

## Review Checklist

### README.md

- [x] One-paragraph description present and accurate
- [x] Quickstart has 5 commands
- [ ] **Commands work end-to-end** — step 5 fails (MF-1)
- [x] Architecture diagram is ASCII and clear
- [x] Directory structure matches actual repo layout
- [ ] **Links all valid** — `specs/event-spine.md` is dead (FA-3)
- [x] Prerequisites list Python 3.10+ and no other deps
- [x] Running tests command is syntactically correct
- [x] Total lines under 200 (127 lines)

### Contributor Guide

- [x] Dev environment setup covers Python version, venv, pytest
- [x] Running locally section explains bootstrap, daemon, client, scripts
- [x] Project structure section explains each directory
- [x] Making changes section covers edit, run tests, verify
- [x] Coding conventions mention stdlib-only, naming, error handling
- [x] Plan-driven development section explains ExecPlans
- [x] Submitting changes covers branch naming, PR template
- [ ] **A new contributor can follow end-to-end** — no tests to run (MF-2)

### Operator Quickstart

- [x] Hardware requirements are realistic
- [x] Installation section shows clone, no pip install
- [x] Configuration documents all env vars
- [x] First boot walkthrough matches bootstrap script output
- [x] Pairing step-by-step matches pair script behavior
- [ ] **Command center access** — localStorage trick is fabricated (MF-3), CORS blocks http.server approach (FA-4)
- [x] Daily operations covers status, mode, events
- [x] Recovery section covers state corruption and daemon restart
- [x] Security notes cover LAN-only binding
- [x] systemd service unit is well-structured

### API Reference

- [x] All 5 endpoints documented
- [x] Each has method, path, auth requirement
- [x] Each has request/response format with examples
- [ ] **Response format accuracy** — `missing_mode` error shape is wrong (FA-1)
- [x] curl examples are syntactically correct
- [x] CLI commands section is comprehensive
- [x] Event kinds table matches code

### Architecture Document

- [x] System overview ASCII diagram is detailed and accurate
- [x] Module guide covers all 4 modules with correct descriptions
- [x] Data flow traces are accurate for the daemon path
- [x] Auth model correctly describes pairing and capability scopes
- [x] Event spine mechanics match code (append-only JSONL, reverse-chronological)
- [x] Design decisions section covers all 5 rationales
- [ ] **Python examples** — `get_events(kind='control_receipt')` would crash (FA-2)

## Nemesis Security Review

### Pass 1: Trust Boundaries & Authority

1. **HTTP API has zero authentication.** Any device on the LAN can POST to `/miner/start`, `/miner/stop`, `/miner/set_mode`. The CLI enforces capability checks, but the HTTP layer does not. The API reference correctly discloses this: "The CLI enforces capabilities; the HTTP API does not." The operator quickstart security section should repeat this warning more prominently.

2. **`0.0.0.0` binding scope.** The operator quickstart recommends `ZEND_BIND_HOST=0.0.0.0` and labels the security section "LAN-Only Binding." Binding to `0.0.0.0` binds to ALL interfaces including public IPs if the machine has one. The "LAN-Only" label is aspirational, not enforced. The docs should say "binds to all interfaces" and advise a firewall rule (which it does, but after the misleading header).

3. **Pairing tokens expire at creation.** `store.py:89` sets `expires = datetime.now(timezone.utc).isoformat()` — the token expires the instant it's created. Token expiry is never checked anywhere. This is cosmetic state that could mislead an operator into thinking token rotation is active.

### Pass 2: Coupled State & Protocol Consistency

1. **Pairing store: full-file rewrite without locking.** `save_pairings()` does `json.dump(pairings, f)` to the entire file. Two concurrent `pair_client()` calls (e.g., two bootstrap scripts) could race and clobber each other. Low risk for single-operator home use, but the architecture doc's "source of truth" framing should note this limitation.

2. **Event spine has no fsync.** `_save_event()` opens in append mode, writes, and closes. No `f.flush()` or `os.fsync()`. A power loss could lose the last event. The architecture doc calls the spine "append-only guarantee" — this is a durability claim it can't fully back.

3. **State directory divergence.** `daemon.py`, `cli.py`, `spine.py`, and `store.py` each independently resolve `STATE_DIR` via `default_state_dir()`. If `ZEND_STATE_DIR` is set for the daemon process but not for a CLI invocation, they write to different directories. The bootstrap script handles this correctly, but ad-hoc CLI usage could diverge. The operator quickstart should note that ZEND_STATE_DIR must be set consistently.

4. **`get_events()` kind filter is broken.** `cli.py:191` passes a raw string to `spine.get_events(kind=kind)`, but the function dereferences `kind.value` (spine.py:87) which crashes on a plain string. This means the `events --kind <filter>` CLI path and all architecture doc examples using string kinds are broken. This is a code bug surfaced by documentation review.

## Recommendations

### To unblock the lane (minimal fixes):

1. **Fix MF-1**: Change `cli.py:78` from `['observe']` to `['observe', 'control']` so the bootstrapped device can exercise the full quickstart.
2. **Fix MF-2**: Add a sentence to the contributor guide acknowledging no tests exist yet.
3. **Fix MF-3**: Remove the `localStorage.setItem('zend_daemon_url', ...)` paragraph from operator-quickstart.md. Keep only the "edit const API_BASE" approach.
4. **Fix FA-1**: Update the `missing_mode` error response in API reference to show `{"error": "missing_mode"}` (no `success` field).
5. **Fix FA-3**: Remove the dead link to `specs/event-spine.md` from README.md.

### Code bugs surfaced by review (separate lane):

1. `spine.get_events()` kind filter crashes on string input — either accept strings or have CLI convert to EventKind.
2. `daemon.py` missing_mode error path omits `success` field — inconsistent with other error responses.
3. `store.create_pairing_token()` sets expiry to now — either implement TTL or remove the field.
4. Daemon lacks CORS headers — blocks cross-origin browser access from a separate static server.

## Final Assessment

**Verdict: Blocked — 3 must-fix issues prevent acceptance.**

The documentation is well-structured, comprehensive, and honest about the system's current limitations. The writing quality is high. The architecture document is the strongest artifact — it accurately describes module responsibilities, data flow, and design rationale. The spec correctly captures the lane's scope and acceptance criteria.

However, the lane's own acceptance criterion #1 — "Fresh clone -> working system in under 10 minutes following README only" — fails because the quickstart's control command will return `unauthorized`. Criterion #4 — "API reference curl examples all work" — is close but the `missing_mode` response shape is wrong. Criterion #2 — "Contributor guide enables test suite execution" — fails because no tests exist.

After the 5 minimal fixes above (3 doc edits, 1 code one-liner, 1 dead link removal), the lane passes.
