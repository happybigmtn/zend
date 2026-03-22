---

## Slice 001 complete

**What was built:**

| Artifact | Status |
|---|---|
| `services/home-miner-daemon/hermes.py` | ✓ 310 lines, all adapter functions |
| `services/home-miner-daemon/daemon.py` | ✓ 5 new Hermes endpoints + control block |
| `services/home-miner-daemon/cli.py` | ✓ 5 hermes subcommands |
| `state/hermes-pairing-store.json` | ✓ Created by `pair()` |
| `outputs/hermes-adapter-implementation/spec.md` | ✓ Written |
| `outputs/hermes-adapter-implementation/review.md` | ✓ Written |

**Integration proof — all 8 pass:**

```
T1  Pair Hermes                           → 200 capabilities=[observe, summarize]
T2  Status without Hermes auth            → 401 HERMES_UNAUTHENTICATED
T3  Status with Hermes auth               → 200 miner snapshot
T4  Append summary                        → 200 appended=true
T5  Read filtered events                  → 200 [hermes_summary] only
T6  Inject user_message to spine          → written
T7  user_message filtered from Hermes     → absent ✓
T8  Hermes control attempt blocked       → 403 HERMES_UNAUTHORIZED ✓
```

**One bug found and fixed during implementation:** `hour` overflow in `pair()` when `validity_hours > 23` — resolved by switching from `replace(hour=now.hour + N)` to `datetime + timedelta(hours=N)`.

**Three honest gaps** documented in `review.md`: unit tests pending, observability logging pending, Agent tab pending. None affect the correctness of this slice.