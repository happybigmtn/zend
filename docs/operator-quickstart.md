# Operator Quickstart

Deploy Zend on home hardware. This guide covers Raspberry Pi, home server, or any
Linux box with Python 3.10+.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Boot](#first-boot)
5. [Pairing a Phone](#pairing-a-phone)
6. [Opening the Command Center](#opening-the-command-center)
7. [Daily Operations](#daily-operations)
8. [Recovery](#recovery)
9. [Security](#security)

---

## Hardware Requirements

### Minimum

- Any Linux device (Raspberry Pi, old laptop, NAS, etc.)
- Python 3.10 or higher
- 512 MB RAM
- 100 MB disk space
- Ethernet or WiFi connection

### Recommended

- Raspberry Pi 4 or better
- Ethernet connection (stable and low-latency)
- 16 GB SD card (for the OS)

### Not Required

- GPU (no mining happens here)
- Large storage (state is minimal)

---

## Installation

### 1. Get the Code

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or higher
```

### 3. No pip Install Needed

Zend uses Python standard library only. No `pip install` required.

### 4. Create State Directory

```bash
mkdir -p state
```

---

## Configuration

### Environment Variables

Create a startup script or set variables in your shell:

```bash
# Daemon binding (default: 127.0.0.1 for local dev)
export ZEND_BIND_HOST=127.0.0.1

# For LAN access on home network:
# export ZEND_BIND_HOST=192.168.1.100  # Your device's IP

# Daemon port (default: 8080)
export ZEND_BIND_PORT=8080

# State directory (default: ./state)
export ZEND_STATE_DIR=/home/pi/zend/state
```

### Running as a Service (systemd)

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/usr/bin/python3 /home/pi/zend/services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/home/pi/zend/state"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend
```

Check status:

```bash
sudo systemctl status zend
```

---

## First Boot

### Run Bootstrap

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

### Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

### Check Initial Status

```bash
python3 services/home-miner-daemon/cli.py status
```

Expected:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 5,
  "freshness": "2026-03-22T12:00:05Z"
}
```

---

## Pairing a Phone

### 1. Start Pairing

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00Z"
}

paired my-phone
capability=observe,control
```

### 2. Verify Pairing

```bash
python3 services/home-miner-daemon/cli.py events --kind pairing_granted --limit 5
```

You should see the pairing granted event.

### Capability Levels

| Capability | What it allows |
|------------|----------------|
| `observe` | Read miner status, view events |
| `control` | Start/stop mining, change modes |

Pair with `observe` for read-only access. Pair with `control` for full control.

---

## Opening the Command Center

### Local Access (Dev)

Open in browser:

```
file:///home/pi/zend/apps/zend-home-gateway/index.html
```

Or serve it:

```bash
cd apps/zend-home-gateway
python3 -m http.server 8081
# Open http://127.0.0.1:8081/
```

### LAN Access (Phone)

1. Find your device's IP:

```bash
hostname -I | awk '{print $1}'
# e.g., 192.168.1.100
```

2. Set `ZEND_BIND_HOST` to that IP before starting the daemon:

```bash
export ZEND_BIND_HOST=192.168.1.100
./scripts/bootstrap_home_miner.sh
```

3. Serve the UI from the IP:

```bash
cd apps/zend-home-gateway
python3 -m http.server 8081 --bind 192.168.1.100
```

4. Open on phone:

```
http://192.168.1.100:8081/
```

### What You'll See

The command center shows:
- **Status Hero** — miner state, mode, freshness
- **Mode Switcher** — paused, balanced, performance
- **Quick Actions** — start, stop buttons
- **Latest Receipt** — most recent event

---

## Daily Operations

### Check Miner Status

```bash
curl http://127.0.0.1:8080/status
```

Or with CLI:

```bash
./scripts/read_miner_status.sh --client my-phone
```

### Start Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action start
```

### Change Mode

```bash
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

Modes:
- `paused` — no mining
- `balanced` — moderate hashrate (~50 kH/s)
- `performance` — maximum hashrate (~150 kH/s)

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --limit 20

# Control receipts only
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

---

## Recovery

### State Corruption

If the daemon fails to start or state seems corrupted:

```bash
# 1. Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# 2. Clear state (back up first!)
mv state state.old

# 3. Recreate state directory
mkdir -p state

# 4. Bootstrap fresh
./scripts/bootstrap_home_miner.sh
```

### Port Already in Use

If port 8080 is busy:

```bash
# Find the process
sudo lsof -i :8080

# Kill it or use a different port
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

Check logs:

```bash
# If running manually:
python3 services/home-miner-daemon/daemon.py

# If running via systemd:
sudo journalctl -u zend -f
```

Common issues:
- Python version too old (need 3.10+)
- Port already in use
- State directory not writable

### View Daemon Logs

The daemon prints to stdout. If running in background:

```bash
# Check if running
ps aux | grep daemon.py

# View PID
cat state/daemon.pid
```

---

## Security

### LAN-Only by Default

Milestone 1 binds to `127.0.0.1`. This means:
- Only processes on the same machine can reach the daemon
- No internet access to the control surface
- Safe for home network deployment

### For LAN Access

If you need phone access from the same network:

```bash
export ZEND_BIND_HOST=192.168.1.100  # Your device's LAN IP
```

**Warning:** Other devices on your network can now reach the daemon. Only do this if your network is trusted.

### Firewall

Consider adding firewall rules:

```bash
# Allow only your phone's IP
sudo ufw allow from 192.168.1.50 to any port 8080
sudo ufw enable
```

### What NOT to Expose

- **Don't expose port 8080 to the internet** — this is a control surface
- **Don't run as root** — the daemon doesn't need root privileges
- **Don't disable authentication** — capability checks are your protection

### Capability Model

Every paired client has explicit capabilities:

| Capability | Can Do |
|------------|--------|
| `observe` | Read status, view events |
| `control` | Start/stop mining, change modes |

Clients without `control` cannot change miner state.

### Audit

Run the local-hashing audit to verify no mining happens on clients:

```bash
./scripts/no_local_hashing_audit.sh --client my-phone
# Output: checked: client process tree, result: no local hashing detected
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start | `./scripts/bootstrap_home_miner.sh` |
| Stop | `./scripts/bootstrap_home_miner.sh --stop` |
| Status | `curl http://127.0.0.1:8080/status` |
| Health | `curl http://127.0.0.1:8080/health` |
| Pair | `./scripts/pair_gateway_client.sh --client <name> --capabilities observe,control` |
| Set mode | `./scripts/set_mining_mode.sh --client <name> --mode balanced` |
| View events | `python3 services/home-miner-daemon/cli.py events --limit 20` |
| Restart | `./scripts/bootstrap_home_miner.sh --stop && ./scripts/bootstrap_home_miner.sh` |

---

*Last updated: 2026-03-22*
