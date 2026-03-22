# Operator Quickstart

Deploy Zend on home hardware. This guide is for someone running the daemon on a Raspberry Pi, NAS, or any Linux box.

## Hardware Requirements

- Any Linux system with Python 3.10+
- Network access (for the command center to reach the daemon)
- Recommended: 512 MB RAM, 1 GB storage
- No GPU required (milestone 1 uses a simulator)

## Installation

Clone the repository:

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

No `pip install` needed. Zend uses Python stdlib only.

## Configuration

Set environment variables before running. Common configuration:

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `./state` | Where identity and pairing records live |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |

### LAN Deployment

To access the command center from a phone on the same network:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

The daemon will listen on all interfaces. Phones on the same LAN can reach it at `http://<daemon-ip>:8080`.

> **Security note**: Binding to `0.0.0.0` exposes the control API on your local network. This is fine for home use behind a router. Do not expose this port to the internet.

## First Boot

### 1. Start the Daemon

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
  "paired_at": "2026-03-22T10:00:00Z"
}
[INFO] Bootstrap complete
```

### 2. Verify the Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

### 3. Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
# {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

## Pairing a Phone

### Option A: Pair via CLI (on the daemon machine)

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device "sarahs-iphone" \
  --capabilities "observe,control"
```

This creates a pairing record for the device. The daemon stores the pairing, not the phone.

### Option B: Pair via Bootstrap Script

The bootstrap script pairs a default device (`alice-phone`) with observe capability:

```bash
./scripts/bootstrap_home_miner.sh
```

## Opening the Command Center

### From a Browser on the Same Machine

```bash
# Open the HTML file directly
open /opt/zend/apps/zend-home-gateway/index.html
# Or
firefox /opt/zend/apps/zend-home-gateway/index.html
```

The command center is a single HTML file. No server required for the UI.

### From a Phone on the Same LAN

1. Find the daemon machine's IP address:

```bash
hostname -I | awk '{print $1}'
# 192.168.1.100
```

2. Open in the phone's browser:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

Or serve the file from a simple HTTP server on the daemon machine:

```bash
cd /opt/zend && python3 -m http.server 9000
```

Then on the phone: `http://192.168.1.100:9000/apps/zend-home-gateway/index.html`

> **Note**: The command center connects to `http://127.0.0.1:8080` by default. On a phone, update the `API_BASE` in the HTML or serve the page from the daemon machine.

## Daily Operations

### Check Status

```bash
# CLI
python3 services/home-miner-daemon/cli.py status

# Or via HTTP
curl http://127.0.0.1:8080/status
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop
```

### Change Mining Mode

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced   # paused | balanced | performance
```

### View Events and Receipts

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Only control receipts
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

## Recovery

### Daemon Won't Start

1. Check if another process is using the port:

```bash
lsof -i :8080
# Kill the process if needed
kill $(lsof -t -i:8080)
```

2. Check the state directory permissions:

```bash
ls -la /opt/zend/state/
```

3. Try starting the daemon directly:

```bash
cd /opt/zend/services/home-miner-daemon
python3 daemon.py
```

### State is Corrupted

If `state/` files are corrupted, you can reset:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove corrupted state
rm -rf /opt/zend/state/

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

> **Warning**: This deletes your principal identity and all pairing records. The daemon will create new ones.

### Phone Can't Connect

1. Verify the daemon is running:

```bash
curl http://127.0.0.1:8080/health
```

2. Check the firewall on the daemon machine:

```bash
# Allow incoming connections on port 8080
sudo ufw allow 8080/tcp
```

3. Verify phone and daemon are on the same subnet.

4. Check the command center's API base URL (it defaults to `127.0.0.1:8080`).

## Systemd Service (Optional)

Run the daemon as a service for automatic startup:

```ini
# /etc/systemd/system/zend-daemon.service
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend/state"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo cp zend-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zend-daemon
sudo systemctl start zend-daemon

# Check status
sudo systemctl status zend-daemon
```

## Security Checklist

- [ ] Daemon binds to `0.0.0.0` only on a trusted LAN
- [ ] Port 8080 is not forwarded or exposed to the internet
- [ ] Router firewall blocks incoming connections on 8080
- [ ] State directory is not world-readable (`chmod 700 state/`)
- [ ] No default or blank pairing tokens
- [ ] Only devices with explicit pairing records can control the miner

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or find and kill the process:

```bash
kill $(cat /opt/zend/state/daemon.pid)
```
