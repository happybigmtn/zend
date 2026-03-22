`★ Insight ─────────────────────────────────────`

**Why the shell injection matters here:** The smoke test at `scripts/hermes_summary_smoke.sh:52` interpolated shell variables directly into Python source code via `'$SUMMARY_TEXT'`. This is a classic "data-as-code" injection pattern — the shell expands the variable before Python parses it, so crafted input can break out of the string literal and execute arbitrary Python. The fix uses `os.environ` to pass data through the environment, keeping the data channel separate from the code channel. This pattern applies broadly: never compose source code from untrusted strings; pass data through structured channels (env vars, stdin, argv with proper quoting).

**The inverted auth model is the subtlest finding:** When you add authentication to a less-privileged endpoint while leaving more-privileged endpoints unauthenticated, you create the illusion of security without the substance. Future contributors may assume "Hermes auth exists, so unauthorized access is blocked" when in reality any LAN client can do everything Hermes can do (and more) without any credentials. The fix isn't necessarily to add auth everywhere in M1 — it's to document the trust boundary clearly so no one builds on a false assumption.

**SpineEvent dict vs attribute access:** The plan's pseudocode uses `e["kind"]` but `SpineEvent` is a `@dataclass`, not a dict. This is a common trap when moving between JSON-centric thinking and Python's type system. Dataclass instances use attribute access (`e.kind`), while their serialized form (`asdict(e)`) produces dicts. The plan was thinking in JSON but writing Python.

`─────────────────────────────────────────────────`

## Review Summary

**Verdict: NOT STARTED — 7 blockers identified, 1 source fix applied.**

### What exists
- Well-defined reference contract (`references/hermes-adapter.md`)
- Event spine with `append_hermes_summary` and `HERMES_SUMMARY` event kind
- Store with pairing infrastructure
- Gateway client with placeholder Agent tab

### What doesn't exist
- `hermes.py` adapter module
- Hermes endpoints in `daemon.py`
- Tests (`test_hermes.py`)
- Token auth infrastructure (plan 006 dependency)
- The plan file itself (`genesis/plans/009-hermes-adapter-implementation.md`)

### Critical findings (3-pass Nemesis review)

| Pass | Finding | Severity |
|------|---------|----------|
| **Trust** | F1: Inverted auth model — Hermes gets auth, control endpoints don't | Design |
| **Trust** | F2: hermes_id is identification, not authentication — no crypto binding | High |
| **Trust** | F3: No revocation mechanism for paired Hermes agents | Medium |
| **State** | S1: Plan uses `e["kind"]` on SpineEvent dataclass (TypeError) | Bug |
| **State** | S2: authority_scope str vs list type mismatch | Bug |
| **State** | S3: `pair_client` raises on duplicate — idempotency claim is false | Bug |
| **State** | S4: Gateway/Hermes capability domains stored without type discriminator | Medium |
| **State** | S5: `create_pairing_token` sets immediate expiration | Bug |
| **State** | S6: Event filtering heuristic (`limit * 2`) is fragile | Low |
| **Ops** | O1: No rate limiting on summary append | Medium |
| **Ops** | O2: No payload size validation | Medium |
| **Ops** | O3: Shell injection in smoke test | **Fixed** |
| **Ops** | O4: No file locking on concurrent spine writes | Low |
| **Ops** | O5: control_receipt leaks user behavior patterns to Hermes | Design question |

### Source fix applied
- `scripts/hermes_summary_smoke.sh`: Replaced shell interpolation into Python source with `os.environ` to eliminate command injection (blocker B7).

### Artifacts delivered
- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`