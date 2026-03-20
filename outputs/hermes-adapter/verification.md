# Hermes Adapter — Verification

**Status:** Milestone 1.1 proof refreshed
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Automated Proof Commands

### Hermes Adapter and Handler Tests

```bash
python3 services/home-miner-daemon/test_adapter.py -v
```

**Outcome:** 21 tests pass.

```text
Ran 21 tests in 0.087s

OK
```

Coverage added in this pass:
- bootstrap failure handling for `bootstrap_hermes.sh`
- `/hermes/connect` missing token and success payload mapping
- `/hermes/status` missing header, missing connection, and unauthorized mapping
- `/hermes/summary` missing summary text mapping

### Syntax Validation

```bash
python3 -m py_compile \
  services/home-miner-daemon/adapter.py \
  services/home-miner-daemon/daemon.py \
  services/home-miner-daemon/__init__.py \
  services/home-miner-daemon/test_adapter.py
```

**Outcome:** all listed files compile without errors.

### Import Surface Check

```bash
python3 -c "import sys; sys.path.insert(0, 'services/home-miner-daemon'); import daemon; print(type(daemon.hermes_adapter).__name__)"
```

**Outcome:**

```text
HermesAdapter
```

### Bootstrap Failure Proof

Deterministic failure-path proof:

```bash
ZEND_STATE_DIR="$(mktemp -d)" \
ZEND_DAEMON_PYTHON=false \
ZEND_STARTUP_RETRIES=1 \
ZEND_STARTUP_INTERVAL_SECONDS=0 \
./scripts/bootstrap_hermes.sh --daemon
```

**Outcome:** script exits non-zero and reports a named gateway failure instead of a misleading partial success transcript.

```text
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[ERROR] GatewayUnavailable: failed to start Zend Home Miner daemon
error_code=GATEWAY_UNAVAILABLE
reason=daemon_process_exited
daemon_log=<temp>/hermes-daemon.log
```

Real entrypoint proof in this sandbox:

```bash
./scripts/bootstrap_hermes.sh
```

**Outcome:** this environment denies loopback socket creation, and the script now fails cleanly with the same named error plus a daemon log path. The stale false-green behavior from the prior artifact is no longer present.

```text
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[ERROR] GatewayUnavailable: failed to start Zend Home Miner daemon
error_code=GATEWAY_UNAVAILABLE
reason=daemon_process_exited
daemon_log=state/hermes-daemon.log
```

Observed daemon log excerpt:

```text
PermissionError: [Errno 1] Operation not permitted
```

## Sufficiency Notes

- Automated proof is sufficient for the code changed in this slice: adapter boundaries, handler response mapping, and honest bootstrap failure reporting are all exercised without requiring a live socket bind.
- No manual proof was required for this proof-hardening pass.
