**Fix complete.** The `home-miner-service:home-miner-service` slice's first proof gate is now unblocked.

## What was wrong

The verify script failed because:

1. **`set -e` + `$(...)` capture bug**: When the bootstrap CLI exited 1 (device already paired), `set -e` caused the script to exit immediately in the subshell before `RESULT=$?` could execute. The `if [ $? -eq 0 ]` check was checking `echo`'s exit code, not the python command's.

2. **Non-idempotent bootstrap**: Re-running the script raised a `ValueError` that was treated as a hard failure instead of an idempotent success.

## What was fixed (`scripts/bootstrap_home_miner.sh`)

- `set +e` / `set -e` guard around the CLI capture to prevent premature exit
- `RESULT=$?` captured immediately after the subshell to get the real exit code
- "already paired" detection treated as idempotent success (exit 0)

## Verification results

| Command | Result |
|---------|--------|
| `./scripts/bootstrap_home_miner.sh` | PASS (exit 0, idempotent on re-run) |
| `GET /health` | `{"healthy":true,"temperature":45.0,"uptime_seconds":0}` |
| `GET /status` | Full miner snapshot with freshness |
| `POST /miner/start` | `{"success":true,"status":"MinerStatus.RUNNING"}` |
| `POST /miner/stop` | `{"success":true,"status":"MinerStatus.STOPPED"}` |