# Operator Quickstart

Deploy and operate Zend Home on home hardware. This guide covers installation, configuration, first boot, pairing, daily operations, recovery, and security.

**Target hardware:** Any Linux machine — desktop, laptop, Raspberry Pi, NAS, or home server. Python 3.10+ required. No GPU, no special mining hardware needed for milestone 1 (uses a miner simulator).

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [First Boot](#4-first-boot)
5. [Pairing a Phone](#5-pairing-a-phone)
6. [Opening the Command Center](#6-opening-the-command-center)
7. [Daily Operations](#7-daily-operations)
8. [Recovery](#8-recovery)
9. [Security](#9-security)

---

## 1. Hardware Requirements

| Requirement | Specification |
|-------------|---------------|
| OS | Linux (Ubuntu 22.04+, Raspberry Pi OS, or similar) |
| Python | 3.10 or later |
| CPU | Any x86_64 or ARM processor |
| RAM | 256 MB free |
| Disk | 50 MB for the repository and state |
| Network | Local LAN (Ethernet or Wi-Fi) |
| Client | Any modern browser on a phone or tablet on the same LAN |

**Raspberry Pi recommendation:** A Pi 3B+ or later is sufficient. The daemon is lightweight.

**Not required:** GPU, FPGA, ASIC, or any mining hardware. Milestone 1 uses a software simulator.

---

## 2. Installation

### 2.1 Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2.2 Verify Python

```bash
python3 --version
# Python 3.10.12  (or later)
```

### 2.3 No pip Install Required

Zend uses only the Python standard library. No `pip install`, no virtual environment, no container needed. Extract the archive and run.

---

## 3. Configuration

The daemon reads configuration from environment variables. Set these before running bootstrap.

### 3.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` for LAN access. |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `$(repo-root)/state` | Where state files are stored |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Base URL for CLI commands |

### 3.2 LAN Deployment (Recommended for Home Use)

To access the command center from your phone on the same network:

```bash
export ZEND_BIND_HOST="0.0.0.0"
export ZEND_BIND_PORT="8080"
```

> **Security note:** Binding to `0.0.0.0` exposes the daemon on your local network. It is not exposed to the internet. See [Security](#9-security) for details.

### 3.3 Persistent Configuration

Add exports to your shell profile for convenience:

```bash
echo 'export ZEND_BIND_HOST="0.0.0.0"' >> ~/.bashrc
echo 'export ZEND_BIND_PORT="8080"' >> ~/.bashrc
source ~/.bashrc
```

Or create a small env file:

```bash
cat > zend-env.sh << 'EOF'
export ZEND_BIND_HOST="0.0.0.0"
export ZEND_BIND_PORT="8080"
EOF
# Source before running: source zend-env.sh
```

---

## 4. First Boot

### 4.1 Run Bootstrap

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Stopping any existing daemon...
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. The PID is saved to `state/daemon.pid`.

### 4.2 Verify the Daemon is Running

```bash
python3 services/home-miner-daemon/cli.py health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### 4.3 Check Initial Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
# → {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

The miner is initially `stopped` in `paused` mode. No work is being done.

---

## 5. Pairing a Phone

The bootstrap script creates a default device named `alice-phone` with `observe` capability. To pair additional devices or set `control` capability:

### 5.1 Pair a New Device

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:05:00.000000+00:00"
}
```

### 5.2 Available Capabilities

| Capability | What it allows |
|------------|----------------|
| `observe` | Read miner status, view events in inbox |
| `control` | Start/stop mining, change operating mode |

A device with `control` can also implicitly `observe`.

### 5.3 List Paired Devices

```bash
# View pairing store directly
cat state/pairing-store.json
```

### 5.4 Pairing Failure Modes

| Error | Meaning | Resolution |
|-------|---------|-----------|
| Device already paired | Name already exists | Use a different `--device` name |
| Token expired | Token validity window passed | Re-run bootstrap to get a new token |

---

## 6. Opening the Command Center

### 6.1 Find the Daemon's IP Address

On the machine running the daemon:

```bash
hostname -I | awk '{print $1}'
# → 192.168.1.100
```

### 6.2 Open in Browser

On your phone or tablet, open your browser and navigate to:

```
http://192.168.1.100:8080
```

(Replace `192.168.1.100` with the actual IP of your machine.)

Open `apps/zend-home-gateway/index.html` directly in your browser (as a `file://` URL or served by any static file server). The HTML file uses `fetch()` to call the daemon's HTTP API at `http://<daemon-ip>:8080`. The daemon itself does not serve static files — it only provides the JSON API endpoints.

### 6.3 What You Should See

The command center shows:
- **Status Hero:** current miner state (`stopped`, `running`) with a green/gray indicator
- **Mode Switcher:** three buttons: Paused, Balanced, Performance
- **Quick Actions:** Start Mining / Stop Mining buttons
- **Bottom Nav:** Home, Inbox, Agent, Device tabs

### 6.4 If the Page Does Not Load

1. **Check the daemon is running:**
   ```bash
   python3 services/home-miner-daemon/cli.py health
   ```
   If this fails, restart the daemon:
   ```bash
   ./scripts/bootstrap_home_miner.sh
   ```

2. **Check firewall:** Ensure port 8080 is allowed on the daemon machine:
   ```bash
   sudo ufw allow 8080/tcp
   ```

3. **Check you're on the same network:** The phone must be on the same LAN as the daemon.

4. **Try from a desktop browser first:** Navigate to `http://127.0.0.1:8080` on the machine running the daemon to verify it works locally.

---

## 7. Daily Operations

### 7.1 Check Miner Status

From the command line:

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

From the browser: open the command center and look at the Status Hero.

### 7.2 Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
```

Or in the browser: tap **Start Mining**.

### 7.3 Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

Or in the browser: tap **Stop Mining**.

### 7.4 Change Operating Mode

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

Valid modes: `paused`, `balanced`, `performance`.

| Mode | Effect |
|------|--------|
| `paused` | Mining simulator is idle |
| `balanced` | Standard simulated workload |
| `performance` | Maximum simulated workload |

Or in the browser: tap the mode button in the Mode Switcher.

### 7.5 View the Event Spine (Operational Inbox)

The event spine records every operation. View it from the CLI:

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt

# Last 5 events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 5
```

In the browser: tap the **Inbox** tab in the bottom nav.

### 7.6 Restart the Daemon After a Reboot

```bash
./scripts/bootstrap_home_miner.sh
```

The state is preserved in `state/`. Pairing records and the event spine survive restarts.

---

## 8. Recovery

### 8.1 State Corruption

If the daemon behaves unexpectedly or the state files are corrupted:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state (deletes all pairing records and event history)
rm -rf state/*

# Restart fresh
./scripts/bootstrap_home_miner.sh

# Re-pair your device
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

This is safe. State is disposable and the system is designed to be bootstrapped from scratch.

### 8.2 Daemon Won't Start (Port in Use)

If the bootstrap script reports the port is already in use:

```bash
# Find and kill the old process
lsof -i :8080
kill <PID>
```

Or:

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### 8.3 Daemon Crashes

Check the process:

```bash
# Is the daemon running?
cat state/daemon.pid
kill -0 $(cat state/daemon.pid) 2>/dev/null && echo "running" || echo "not running"

# Restart
./scripts/bootstrap_home_miner.sh
```

### 8.4 Phone Can't Reach the Command Center

1. Verify daemon is running: `curl http://127.0.0.1:8080/health`
2. Check `ZEND_BIND_HOST` is `0.0.0.0` (not `127.0.0.1`)
3. Check the phone is on the same network
4. Check local firewall: `sudo ufw allow 8080/tcp`

### 8.5 Full Reset

To completely reset the system:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

---

## 9. Security

### 9.1 LAN-Only by Default

The daemon binds to `127.0.0.1` by default. To allow phone access, set `ZEND_BIND_HOST="0.0.0.0"`. This exposes the daemon on your local network only. **It is not accessible from the internet** unless you have port forwarding configured (not recommended).

### 9.2 No Authentication on Local Network

Milestone 1 uses capability-scoped pairing records rather than password-based auth. Anyone on your LAN who knows your device name can issue commands your device is authorized for. Pairing records are stored in `state/pairing-store.json` on the machine.

### 9.3 What Not to Expose

- **Do not** forward port 8080 to the internet
- **Do not** bind to `0.0.0.0` on a machine with public internet exposure
- **Do not** store sensitive data in the state directory

### 9.4 Mining Never Happens on the Phone

The `apps/zend-home-gateway/index.html` file is a pure control surface. It sends HTTP requests to the daemon and displays responses. No hashing, no mining work, no CPU-intensive operations run on the client device.

You can verify this by inspecting the HTML file — it contains no hashing code, no WebAssembly, and no CPU-intensive JavaScript.

### 9.5 Firewall Recommendations

Allow only the daemon port on your local interface:

```bash
# Allow from LAN only
sudo ufw allow from 192.168.0.0/16 to any port 8080
sudo ufw deny 8080
```

### 9.6 Upgrading

To pull the latest code and restart:

```bash
git pull
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

Pairing records in `state/` are preserved across upgrades unless the upgrade includes a state schema migration (which will be documented in the release notes).

---

## Quick Reference Card

```bash
# Start daemon
./scripts/bootstrap_home_miner.sh

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Check health
python3 services/home-miner-daemon/cli.py health

# Get miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# Start mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop

# Set mode (paused | balanced | performance)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# View events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Pair a device
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control

# Reset state
rm -rf state/* && ./scripts/bootstrap_home_miner.sh
```
