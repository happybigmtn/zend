# Operator Quickstart

This guide walks you through deploying Zend on home hardware — a Raspberry Pi,
a mini PC, or any Linux machine on your network. No cloud, no subscription,
no port forwarding required for local use.

## Hardware Requirements

| Requirement | Specification |
|-------------|---------------|
| OS | Linux (Debian, Ubuntu, Raspberry Pi OS, or similar) |
| Python | 3.10 or higher |
| RAM | 512 MB minimum |
| Storage | 1 GB free space |
| Network | Ethernet or Wi-Fi on your LAN |
| Access | SSH or terminal |

Check your Python version:

```bash
python3 --version
```

If it's below 3.10, install Python 3.10+:

```bash
sudo apt update && sudo apt install -y python3.10 python3.10-venv
```

## Installation

### 1. Clone the repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

No `pip install`, no build step — the daemon is a single Python file.

### 2. Verify the files

```bash
ls services/home-miner-daemon/
# Should show: __init__.py cli.py daemon.py spine.py store.py

ls scripts/
# Should show: bootstrap_home_miner.sh pair_gateway_client.sh ...
```

## Configuration

Zend uses environment variables. Set them in your shell or in a startup script.

### Environment Variables

| Variable | Default | Recommended | Description |
|----------|---------|-------------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | `0.0.0.0` | Bind address |
| `ZEND_BIND_PORT` | `8080` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `state/` | `state/` | State directory |
| `ZEND_TOKEN_TTL_HOURS` | — | `720` (30 days) | Pairing token TTL |

### LAN Access (recommended for home use)

To access the command center from your phone on the same network:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

> **Security note**: Binding to `0.0.0.0` exposes the daemon on your LAN.
> It is not internet-facing by default. Do not port-forward this to the internet.

### Persistent Configuration

Create a startup script at `/opt/zend/start-zend.sh`:

```bash
#!/bin/bash
cd /opt/zend
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
exec python3 services/home-miner-daemon/daemon.py
```

Make it executable:

```bash
chmod +x /opt/zend/start-zend.sh
```

## First Boot

### 1. Bootstrap the daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "..."
}
[INFO] Bootstrap complete
```

### 2. Verify the daemon is running

```bash
curl http://localhost:8080/health
```

Expected output:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Verify miner status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
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

## Pairing a Phone

The default bootstrap pairs a device named `alice-phone` with `observe` capability.
To pair additional devices or grant `control` capability:

### 1. Pair a new device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T..."
}
```

### 2. Verify pairing

```bash
cat state/pairing-store.json
```

You should see both `alice-phone` and `my-phone` in the pairing records.

### Pairing capabilities

| Capability | What it allows |
|------------|---------------|
| `observe` | Read miner status, view events |
| `control` | Start, stop, change mining mode |

Grant `control` only to devices you trust. You can always pair a device with
`observe` first and upgrade later:

```bash
./scripts/pair_gateway_client.sh --client kitchen-tablet --capabilities observe
```

## Opening the Command Center

### From a phone or tablet on your LAN

1. Find the IP address of your home server:

```bash
hostname -I | awk '{print $1}'
```

2. Open the command center in a browser:

```
http://<server-ip>:8080/status  # Shows current miner status as JSON
```

Or open the HTML gateway directly from the repo:

```
http://<server-ip>:8080/        # Won't work — HTML is a local file
```

To serve the HTML gateway, copy it to a web server or use Python:

```bash
cd /opt/zend
python3 -m http.server 9000 --directory apps/zend-home-gateway
```

Then open: `http://<server-ip>:9000/`

### From the same machine

```bash
open apps/zend-home-gateway/index.html
# or
xdg-open apps/zend-home-gateway/index.html
```

## Daily Operations

### Check miner status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Or use the CLI on the server:

```bash
curl http://localhost:8080/status
```

### Start mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
```

### Stop mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop
```

### Change mining mode

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Modes:
- `paused` — no mining
- `balanced` — 50 kH/s simulated
- `performance` — 150 kH/s simulated

### View recent events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone
```

### View only control receipts

```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 20
```

## Running as a Service

### systemd (recommended)

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
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

### Check logs

```bash
journalctl -u zend -f
```

## Recovery

### State is corrupted

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

This creates a fresh `PrincipalId` and re-pairs `alice-phone`.

### Daemon won't start (port in use)

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill it
sudo kill <PID>

# Or use a different port
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

Update your command center URL accordingly.

### Daemon starts but HTML gateway can't connect

1. Verify the daemon is running:

```bash
curl http://localhost:8080/health
```

2. Check the bind address:

```bash
# It should be 0.0.0.0, not 127.0.0.1
grep BIND_HOST services/home-miner-daemon/daemon.py
```

3. Check firewall on the server:

```bash
sudo ufw allow 8080/tcp
```

### Pairing token expired or invalid

Tokens are generated at bootstrap time. To re-pair:

```bash
# Delete the device from the pairing store
# Edit state/pairing-store.json and remove the device entry

# Or clear everything and re-bootstrap
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Python version too old

```bash
# Check version
python3 --version

# On Raspberry Pi OS, install Python 3.10
sudo apt update
sudo apt install -y python3.10 python3.10-venv

# Use python3.10 explicitly
python3.10 services/home-miner-daemon/daemon.py
```

## Security

### LAN-only by default

Zend binds to a private interface by default. It does not expose any control
surface to the internet.

### What to check

1. **Firewall**: Only allow port 8080 on your LAN interface, not WAN
2. **Pairing tokens**: They expire after 30 days by default
3. **Control capability**: Only grant `control` to devices you own
4. **No plaintext**: Event spine payloads are encrypted at rest

### What not to do

- Do not expose port 8080 to the internet
- Do not grant `control` to untrusted devices
- Do not share your `state/` directory
- Do not run the daemon as root in production (use a dedicated user)

## Uninstallation

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove the service if installed
sudo systemctl disable zend
sudo rm /etc/systemd/system/zend.service
sudo systemctl daemon-reload

# Remove the repository
sudo rm -rf /opt/zend

# Optionally remove state (your principal identity is here)
rm -rf state/
```

## Quick Reference

```bash
# Start
./scripts/bootstrap_home_miner.sh

# Check health
curl http://localhost:8080/health

# Status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Change mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# View events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Reset state
rm -rf state/* && ./scripts/bootstrap_home_miner.sh
```
