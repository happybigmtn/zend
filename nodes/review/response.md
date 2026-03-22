Both artifacts are written. Here's the summary:

---

## Lane Outcome

The `specify` stage failed at the **meta-orchestration level** — the Fabro CLI agent exhausted its output budget before producing a well-formed spec. The four target lanes were never investigated.

## Findings (5 bugs, 6 missing features, 4 security issues)

### Correctness Bugs
| Bug | File | Severity |
|---|---|---|
| Pairing tokens expire at birth | `store.py:89` | **Critical** — blocks bootstrap |
| Bootstrap not idempotent | `cli.py:78` | **High** — second run fails |
| `--client` omission bypasses auth | `cli.py:47` | **Medium** |
| `get_pairing_by_device(None)` unhandled | `cli.py:143` | **Low** |
| `get_events` string vs enum mismatch | `spine.py:82` | **Low** |

### Security (Nemesis review)
1. **Daemon HTTP API has zero authentication** — any LAN peer can start/stop the miner. The capability model only exists in the CLI layer, which the HTTP surface doesn't call. This is enforcement at the wrong layer.
2. **Observer → controller escalation** — `pair_client` grants any requested capabilities with no approval flow.
3. **Hermes has unrestricted spine access** — no adapter exists; smoke test calls `append_hermes_summary` via direct import.
4. **Pairing store ↔ spine are not transactional** — spine append failure leaves orphan pairing records, violating the "spine is source of truth" contract.

### What's missing
No HTTP auth, no Hermes adapter, no control command serialization, no encryption on spine (spec says "encrypted"), no tests, no `upstream/manifest.lock.json`.

### Verdict
**Not shippable.** Scaffold is ~50% of milestone 1 and worth preserving. The single highest-leverage fix is adding HTTP-layer authentication to the daemon — it unblocks all four lanes simultaneously.

Artifacts:
- `outputs/stabilize-failed-lanes/spec.md` — root causes + acceptance criteria
- `outputs/stabilize-failed-lanes/review.md` — full review with Nemesis security passes