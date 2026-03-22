# Operator Quickstart

This guide walks an operator through deploying Zend on home hardware — a
Raspberry Pi, a mini PC, or any Linux box on your network.

---

## Hardware Requirements

| Requirement | Value |
|---|---|
| OS | Linux (Debian, Ubuntu, Raspberry Pi OS) |
| Python | 3.10 or later |
| Disk | ~50 MB for repo + state |
| RAM | 256 MB free |
| Network | Ethernet or Wi-Fi on your LAN |
| Ports | TCP 8080 (daemon, not public-facing) |

No GPU, no mining hardware required for milestone 1. The miner simulator
proves the control surface without real mining work.

---

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python Version

```bash
python3 --version
# Must be 3.10 or later
```

If not, install Python 3.10+:

```bash
sudo apt update && sudo apt install -y python3.11
```

### 3. No pip install Required

The daemon uses only Python standard library modules. No external dependencies.

---

## Configuration

Set environment variables to customize the daemon before starting.

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to. Use `0.0.0.0` for all interfaces (not recommended for milestone 1) |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `$(repo)/state` | Where state files are written |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Pairing token validity window (not yet enforced, see `references/error-taxonomy.md`) |

Example — bind to all local interfaces for LAN access:

```bash
export ZEND_BIND_HOST="0.0.0.0"
export ZEND_BIND_PORT="8080"
export ZEND_STATE_DIR="/opt/zend/state"
```

---

## First Boot

### Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

### Verify the Daemon Is Running

```bash
curl http://127.0.0.1:8080/health
```

Expected output:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T..."
}
```

---

## Pairing a Phone

From a browser on your phone (or any device on the same LAN), open the
command center:

```
file:///opt/zend/apps/zend-home-gateway/index.html
```

If opening the file directly doesn't work (some browsers block local file access
to HTTP), serve the HTML file:

```bash
python3 -m http.server 9000 --directory apps/zend-home-gateway
```

Then open: `http://<your-server-ip>:9000/`

### Pair via CLI (Alternative)

Pair from the server directly:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

This creates a pairing record and prints the result.

---

## Daily Operations

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
```

Or from the HTML command center — the status hero shows current state, mode,
hashrate, and freshness timestamp.

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
```

Or use the Start Mining button in the HTML command center.

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop
```

### Change Mining Mode

Modes: `paused`, `balanced`, `performance`

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

### View the Event Log

```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

---

## Recovery

### Daemon Won't Start — Port in Use

```bash
# Check what's using the port
lsof -i :8080
# or
ss -tlnp | grep 8080

# Stop the conflicting process, or change ZEND_BIND_PORT:
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start — State Corrupt

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Restart from scratch
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Connect to Command Center

1. Verify the daemon is running: `curl http://127.0.0.1:8080/health`
2. Verify both devices are on the same LAN subnet
3. Check firewall rules: `sudo ufw status` — allow TCP 8080 for LAN access
4. If using the file URL, try the HTTP server method instead:

   ```bash
   python3 -m http.server 9000 --directory apps/zend-home-gateway
   ```
   Then open `http://<server-ip>:9000/` from your phone's browser.

### Client Says "Unauthorized"

The device lacks the `control` capability. Re-pair with control:

```bash
./scripts/pair_gateway_client.sh \
  --client my-phone --capabilities observe,control
```

---

## Security Notes

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. It is not reachable from outside
your local network. Do not change `ZEND_BIND_HOST` to a public IP without
adding authentication and TLS.

### What Not to Expose

- The daemon HTTP port (8080) should never be port-forwarded to the internet
- The state directory (`state/`) contains the pairing store and event spine —
  protect it with filesystem permissions: `chmod 700 state/`
- Pairing tokens are short-lived in intent (see `references/error-taxonomy.md`);
  token TTL enforcement is not yet implemented in milestone 1

### Hardening Checklist

- [ ] Daemon runs as a non-root user
- [ ] `state/` directory is owned by the daemon user with `chmod 700`
- [ ] No public IP binding without auth
- [ ] Pairing records reviewed periodically (`python3 cli.py events`)

---

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or kill by PID (stored in `state/daemon.pid`):

```bash
kill $(cat state/daemon.pid)
```
