## Summary

**Issue Fixed**: `OSError: [Errno 98] Address already in use` when starting the home miner daemon.

**Root Cause**: A stale daemon from a previous run was still bound to port 18080. The `start_daemon` function only checked its own PID file, not whether the port was occupied by another process.

**Fix Applied** (`scripts/bootstrap_home_miner.sh`):
```bash
# Kill any process already on our port (stale orphan from previous run)
if command -v lsof >/dev/null 2>&1; then
    STALE_PID=$(lsof -ti "$BIND_HOST:$BIND_PORT" 2>/dev/null || true)
    if [ -n "$STALE_PID" ]; then
        log_warn "Killing stale process (PID: $STALE_PID) on port $BIND_PORT"
        kill -9 "$STALE_PID" 2>/dev/null || true
        sleep 1
    fi
fi
```

**Verification**: All proof commands pass:
- Daemon starts successfully on port 18080
- Health check responds
- Pairing is idempotent (already paired from prior run)
- Miner status reads correctly
- Control action (set_mode) accepted with receipt
- No local hashing detected (gateway client issues control only)

`★ Insight ─────────────────────────────────────`
- **PID files aren't sufficient for port cleanup**: A daemon crash can leave the port bound even though the PID is dead. Robust startup scripts must check port availability directly, not just PID file state.
- **lsof vs fuser**: `lsof -ti` is widely available and returns PIDs directly bound to a port, making it portable across Linux distributions for this cleanup pattern.
`─────────────────────────────────────────────────`

**Artifacts Updated**:
- `verification.md` — documented actual proof outcomes and fix applied
- `integration.md` — reviewed, accurate
- `implementation.md` — unchanged (still accurate)
- `quality.md` — not hand-authored per stage rules
- `promotion.md` — not modified per stage rules