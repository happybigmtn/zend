# Operator Quickstart

This guide walks you through deploying Zend on home hardware (Raspberry Pi, home server, NAS, etc.).

## Hardware Requirements

- Any Linux system with Python 3.10+
- ARM (Raspberry Pi 3+) or x86_64
- 512 MB RAM minimum
- Local network connection

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Should print Python 3.10.x or later
```

### 3. Bootstrap the Daemon

```bash
sudo -u $ZEND_USER ./scripts/bootstrap_home_miner.sh
```

This starts the daemon on `127.0.0.1:8080` and creates your principal identity.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | Listen port |
| `ZEND_STATE_DIR` | `./state` | State directory path |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

### LAN Access Configuration

By default, the daemon binds to `127.0.0.1` (localhost only). To allow devices on your local network to connect:

```bash
# Find your LAN interface IP
ip addr show | grep inet

# Example: 192.168.1.100
export ZEND_BIND_HOST=192.168.1.100
./scripts/bootstrap_home_miner.sh
```

**Warning**: Only bind to a private LAN interface. Never expose the daemon to the internet.

## First Boot

### 1. Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected response:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Check Status

```bash
curl http://127.0.0.1:8080/status
```

Expected response:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

## Pairing a Phone

### 1. Find Your Daemon's LAN Address

On the host running the daemon:

```bash
hostname -I | awk '{print $1}'
```

### 2. Open the Command Center

On your phone, open a browser and navigate to:

```
file:///opt/zend/apps/zend-home-gateway/index.html
```

Or, if serving the file:

```bash
cd /opt/zend/apps/zend-home-gateway
python3 -m http.server 8081
```

Then on your phone: `http://<host-ip>:8081/index.html`

### 3. Verify Connection

The command center should show:
- Miner status (stopped/paused)
- Temperature
- Freshness timestamp

If you see "Unable to connect to Zend Home", check:
- Daemon is running (`ps aux | grep daemon.py`)
- URL is correct (should point to daemon's address)
- No firewall blocking the connection

## Daily Operations

### Checking Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status

# Via HTTP
curl http://127.0.0.1:8080/status
```

### Starting Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

### Stopping Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### Changing Mode

```bash
# Balanced (normal use)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Performance (full power)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode performance

# Paused (off)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode paused
```

### Viewing Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Control receipts only
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Last 5 events
python3 services/home-miner-daemon/cli.py events --limit 5
```

### Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Restarting the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

## Recovery

### State Becomes Corrupt

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start (Port in Use)

```bash
# Check what's using the port
lsof -i :8080

# Kill existing process
kill <PID>

# Or change the port
export ZEND_BIND_PORT=8082
./scripts/bootstrap_home_miner.sh
```

### Pairing Problems

To re-pair a device:

```bash
# Remove existing pairing
python3 -c "
import json
with open('state/pairing-store.json') as f:
    store = json.load(f)
# Remove device entries
# Then re-bootstrap
"

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

## Security

### LAN-Only Binding

The daemon defaults to `127.0.0.1` (localhost only). This means:
- Only processes on the same machine can connect
- No remote access by default
- Safe for untrusted networks

### If You Enable LAN Access

Only bind to your private network:
- ✅ `192.168.x.x` (private LAN)
- ✅ `10.x.x.x` (private LAN)
- ❌ `0.0.0.0` (all interfaces, including potential internet exposure)
- ❌ Public IP addresses

### Firewall Configuration

```bash
# Allow local access only (recommended)
ufw allow from 192.168.1.0/24 to any port 8080

# Or disable entirely for localhost-only
ufw deny 8080/tcp
```

### What Not to Expose

- Never expose port 8080 to the internet
- Never run the daemon as root
- Never store sensitive data in the state directory without encryption

## Service Management

### Systemd Service (Recommended for Production)

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=zend
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=127.0.0.1"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend/state"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend
sudo systemctl start zend
sudo systemctl status zend
```

## Monitoring

### Health Check Script

```bash
#!/bin/bash
HEALTH=$(curl -s http://127.0.0.1:8080/health)
if echo "$HEALTH" | grep -q '"healthy": true'; then
    echo "OK: Zend Home is healthy"
    exit 0
else
    echo "WARN: $HEALTH"
    exit 1
fi
```

Add to cron for monitoring:

```bash
*/5 * * * * /opt/zend/scripts/health_check.sh || /opt/zend/scripts/bootstrap_home_miner.sh
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Unable to connect" in browser | Daemon not running | `./scripts/bootstrap_home_miner.sh` |
| Command fails with unauthorized | Device lacks capability | Pair with `control` capability |
| Port already in use | Another process on port | `lsof -i :8080` to find, then `kill` |
| Status shows stale data | Daemon unresponsive | Restart: `./scripts/bootstrap_home_miner.sh --stop && ./scripts/bootstrap_home_miner.sh` |
| Pairing fails | Device already paired | Clear state: `rm -rf state/* && ./scripts/bootstrap_home_miner.sh` |
