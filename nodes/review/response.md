`★ Insight ─────────────────────────────────────`
**The "locked door, open window" pattern** — The adapter correctly restricts Hermes to observe+summarize at the module level. But the daemon's miner control endpoints (`/miner/start`, etc.) have zero authentication. The adapter is a capability boundary sitting in front of an ungated resource. This is a common pattern in layered systems where auth lands in a different plan — what matters is that the review documents it honestly rather than claiming protection that doesn't exist.

**Allowlist vs denylist for event filtering** — `HERMES_READABLE_EVENTS` is an allowlist (only listed kinds pass through). This is the correct pattern: when new `EventKind` values are added to the spine, they're hidden from Hermes by default. A denylist (block `user_message`) would leak new event types.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONAL APPROVE**

### What's sound
- The adapter module correctly enforces observe+summarize capability boundary
- Event filtering uses an allowlist (safe by default for new event kinds)
- 19/19 tests pass, covering happy paths, error cases, and boundary conditions
- Idempotent pairing, proper error messages, clean separation from daemon

### What I fixed (2 bugs)
1. **CLI `--capabilities` parsing** (`cli.py:216`): raw string was passed instead of `list` — would crash on any non-default input
2. **State dir inconsistency** (`hermes.py`): inline calculation without `.resolve()` didn't match the codebase convention used by `spine.py`, `store.py`, `daemon.py`

### Critical finding: prior review contained a false claim
The auto-review stated "Control endpoints require gateway auth, not Hermes auth." This is false — `daemon.py:259-271` has **zero authentication** on `/miner/start`, `/miner/stop`, `/miner/set_mode`. Any LAN client can call them. This is pre-existing (not introduced by this slice), but the review must not claim a protection that doesn't exist.

### Remaining blockers for truthful end-to-end invariant
| Blocker | Required for |
|---------|-------------|
| Daemon auth on `/miner/*` (plan 006) | "Hermes cannot control" to hold at HTTP level |
| Token signing (plan 006) | Token forgery prevention |
| Agent tab update | UX completeness (deferred per plan) |

Full findings in `outputs/hermes-adapter-implementation/review.md` — 6 security findings (S-1 through S-6) and 2 bugs fixed (B-1, B-2).