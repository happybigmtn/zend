Fixup complete. The verification failure was caused by stale daemon processes holding ports (`TIME_WAIT` state) from previous runs.

**Root cause**: `start_daemon()` used `kill -0 $PID` which only checks process existence—not port availability. When a daemon crashes, the port stays in `TIME_WAIT` for ~60s while the PID becomes invalid.

**Fix applied**: Added `is_port_in_use()` + `fuser -k ${PORT}/tcp` to `scripts/bootstrap_home_miner.sh` to proactively clean up stale ports before binding.

**Verification**: All 5 automated proof commands now pass:
1. Bootstrap daemon ✅
2. Pair gateway client ✅  
3. Read miner status ✅
4. Set mining mode ✅
5. No local hashing audit ✅

Artifacts updated:
- `verification.md` — documented the second fixup iteration