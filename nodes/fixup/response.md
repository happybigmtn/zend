**Fixup complete.** The `./scripts/bootstrap_home_miner.sh` first proof gate now passes.

**What was fixed:**
- `scripts/bootstrap_home_miner.sh`: `stop_daemon()` now calls `fuser -k "$BIND_PORT/tcp"` to kill any process holding the port before starting, and also kills orphaned `daemon.py` processes from any prior run.

**What was verified:**
- Bootstrap creates principal identity and alice-phone pairing
- bob-phone pairs with `observe,control` capability
- `set_mode balanced` accepted with control capability
- Spine events returns 5 events with proper authorization

**Artifacts updated:**
- `verification.md` — First Proof Gate marked PASSED (after fix), Pre-existing Issue documented as FIXED, Verification Environment updated to port 18080

`★ Insight ─────────────────────────────────────`
**`fuser` vs `SO_REUSEADDR`**: `SO_REUSEADDR` only helps when the socket is in `TIME_WAIT` state (kernel hasn't fully released it yet). When another process is actively listening on the port, you must kill that process first — `fuser` does this by finding which process holds the port.
**Port isolation per fabro run**: Each fabro run gets its own port (18080 via `ZEND_BIND_PORT` env). Without `fuser`, a daemon from run A would block run B's bootstrap unless explicitly stopped. Now `stop_daemon` proactively clears the port regardless of which run started the prior daemon.
`─────────────────────────────────────────────────`