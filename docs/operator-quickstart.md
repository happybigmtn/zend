# Operator Quickstart

Deploy Zend on a Raspberry Pi, home server, or any Linux box. This guide walks you through installation, configuration, first boot, and daily operations.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|------------|
| CPU | Single-core ARM | Multi-core ARM/x86 |
| RAM | 512 MB | 1 GB+ |
| Storage | 1 GB free | 4 GB+ free |
| OS | Linux (any) | Raspberry Pi OS, Ubuntu Server |
| Python | 3.10+ | 3.10+ |

No GPU required. No special mining hardware required for milestone 1 (uses simulator).

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version  # Must be 3.10 or higher
```

If your system has an older Python, install 3.10+:

```bash
# Raspberry Pi / Debian
sudo apt update && sudo apt install -y python3 python3-venv

# Or use pyenv
curl https://pyenv.run | bash
pyenv install 3.10.14
pyenv global 3.10.14
```

### 3. No pip Install Needed

Zend uses only Python standard library. No external packages to install.

## Configuration

### Environment Variables

Create `/etc/zend/environment` or set variables in your shell:

```bash
# Required for systemd service
export ZEND_STATE_DIR="/var/lib/zend"
export ZEND_BIND_HOST="0.0.0.0"      # LAN-only binding
export ZEND_BIND_PORT="8080"
export ZEND_DAEMON_URL="http://localhost:8080"
```

### State Directory

```bash
sudo mkdir -p /var/lib/zend
sudo chown $USER:$USER /var/lib/zend
```

### Firewall (Optional)

If you want to access the command center from other devices on your LAN:

```bash
# Allow access from LAN
sudo ufw allow from 192.168.0.0/24 to any port 8080
```

**Warning:** The daemon is LAN-only by design. Do not expose port 8080 to the internet.

## First Boot

### 1. Start the Daemon

```bash
# From the repo directory
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Stopping Zend Home Miner Daemon
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-23T12:00:00Z"
}
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Check Status

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
  "uptime_seconds": 0,
  "freshness": "2026-03-23T12:00:01Z"
}
```

## Pairing a Phone

### 1. Find Your Machine's LAN IP

```bash
hostname -I | awk '{print $1}'
```

Example: `192.168.1.100`

### 2. Configure Daemon for LAN Access

```bash
# Stop daemon first
./scripts/bootstrap_home_miner.sh --stop

# Start with LAN binding
ZEND_BIND_HOST="192.168.1.100" ./scripts/bootstrap_home_miner.sh
```

Or set in environment:

```bash
export ZEND_BIND_HOST="192.168.1.100"
./scripts/bootstrap_home_miner.sh
```

### 3. Open the Command Center

On your phone's browser, navigate to:

```
http://192.168.1.100:8080
```

Or open the file directly:

```
file:///opt/zend/apps/zend-home-gateway/index.html
```

For file access, the HTML connects to `http://127.0.0.1:8080`. You may need to serve the file via HTTP:

```bash
# Serve the command center
cd /opt/zend/apps/zend-home-gateway
python3 -m http.server 3000
```

Then open `http://192.168.1.100:3000` on your phone.

### 4. Pair via Script

```bash
# Pair with observe + control
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Daily Operations

### Checking Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status

# Via HTTP
curl http://127.0.0.1:8080/status

# Via script
./scripts/read_miner_status.sh --client my-phone
```

### Changing Mining Mode

```bash
# Pause mining
./scripts/set_mining_mode.sh --client my-phone --mode paused

# Balanced mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Performance mode
./scripts/set_mining_mode.sh --client my-phone --mode performance
```

### Starting/Stopping Mining

```bash
# Start
./scripts/set_mining_mode.sh --client my-phone --action start

# Stop
./scripts/set_mining_mode.sh --client my-phone --action stop
```

### Viewing Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt

# Latest 20 events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20
```

## Recovery

### Daemon Won't Start

```bash
# Check if port is in use
sudo lsof -i :8080

# Kill existing process
pkill -f "daemon.py" || true

# Try again
./scripts/bootstrap_home_miner.sh
```

### State Corruption

```bash
# Full state reset (destroys all pairing data)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh

# Re-pair devices
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Daemon Crashed

```bash
# Check for crash logs
journalctl --user -u zend.service --lines 50

# Restart
sudo systemctl restart zend
```

### Pairing Issues

```bash
# List paired devices
python3 -c "
import sys
sys.path.insert(0, 'services/home-miner-daemon')
from store import load_pairings
for id, p in load_pairings().items():
    print(f\"{p['device_name']}: {p['capabilities']}\")
"

# Revoke and re-pair
rm state/pairing-store.json
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Running as a Service (systemd)

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_STATE_DIR=/var/lib/zend"
Environment="ZEND_BIND_HOST=192.168.1.100"
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

# Check status
sudo systemctl status zend
```

## Security Notes

### LAN-Only by Design

The daemon binds to a private local interface. Phase one intentionally does not expose internet-facing control surfaces.

### What to Check

- [ ] Daemon binds to expected interface only (`ZEND_BIND_HOST`)
- [ ] No port forwarding for 8080 on your router
- [ ] No firewall rule allowing WAN access to 8080
- [ ] State directory has correct permissions

### What Not to Expose

- [ ] Port 8080 directly to the internet
- [ ] The state directory (`state/`) to other users
- [ ] The event spine JSONL file to unauthorized clients

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop zend
sudo systemctl disable zend

# Remove service file
sudo rm /etc/systemd/system/zend.service
sudo systemctl daemon-reload

# Remove state (optional)
rm -rf /var/lib/zend

# Remove repo
sudo rm -rf /opt/zend
```
