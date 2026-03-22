# Operator Quickstart

Deploy Zend on your home hardware. This guide walks you through installation, configuration, and daily operations.

## Hardware Requirements

- **Any Linux system** with Python 3.10+
- **Raspberry Pi 4** or similar single-board computer
- **x86_64 server** or desktop
- **Network access** — phone and daemon must be on the same LAN

## Installation

### 1. Clone the Repository

SSH into your home server and run:

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version  # Must be 3.10 or later
```

If you need to install Python 3.10+:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install python3
```

### 3. No Additional Dependencies

Zend uses only Python standard library. No `pip install`, no package managers needed.

## Configuration

### Environment Variables

Create a systemd service file at `/etc/systemd/system/zend-daemon.service`:

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
Environment="ZEND_STATE_DIR=/opt/zend/state"
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Configuration Reference

| Variable | Default | Recommended | Description |
|----------|---------|-------------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | `0.0.0.0` | `0.0.0.0` for LAN access |
| `ZEND_BIND_PORT` | `8080` | `8080` | HTTP port (firewall must allow) |
| `ZEND_STATE_DIR` | `./state` | `/opt/zend/state` | Persistent state directory |
| `ZEND_TOKEN_TTL_HOURS` | `24` | `168` (1 week) | Pairing token validity |

### Security Considerations

**ZEND_BIND_HOST=0.0.0.0** makes the daemon accessible from your LAN. This is required for the phone to connect, but:

- Do NOT expose port 8080 to the internet
- Use firewall rules to block external access
- Consider VPN for remote access instead of port forwarding

## First Boot

### 1. Start the Daemon

```bash
# Development mode (binds to localhost only)
/opt/zend/scripts/bootstrap_home_miner.sh

# Production mode (binds to all interfaces)
/opt/zend/scripts/bootstrap_home_miner.sh --daemon
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
```

### 2. Enable the Service (systemd)

```bash
sudo systemctl enable zend-daemon
sudo systemctl start zend-daemon

# Check status
sudo systemctl status zend-daemon
```

### 3. Verify Connectivity

From another machine on your LAN:

```bash
curl http://<server-ip>:8080/health
```

Expected response:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Pairing a Phone

### 1. Find Your Server's LAN IP

On the server:
```bash
hostname -I
```

### 2. Update the Command Center

Edit `apps/zend-home-gateway/index.html` and change the API base URL:

```javascript
// Find this line and update the IP:
const API_BASE = 'http://192.168.1.100:8080';  // Your server IP
```

Or serve it from the daemon directly (see Future Enhancements).

### 3. Open in Phone's Browser

Navigate to `http://<server-ip>:8080` on your phone's browser, or copy the `index.html` file to your phone and open it.

### 4. Verify Pairing

On the server, check paired devices:

```bash
cat /opt/zend/state/pairing-store.json
```

## Daily Operations

### Check Miner Status

```bash
python3 /opt/zend/services/home-miner-daemon/cli.py status --client alice-phone
```

### Start/Stop Mining

```bash
# Start
python3 /opt/zend/services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop
python3 /opt/zend/services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### Change Mining Mode

```bash
# Pause (lowest power, no hashing)
python3 /opt/zend/services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode paused

# Balanced (moderate power, standard hashrate)
python3 /opt/zend/services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Performance (high power, maximum hashrate)
python3 /opt/zend/services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode performance
```

### View Event Log

```bash
# Recent events
python3 /opt/zend/services/home-miner-daemon/cli.py events --client alice-phone --limit 10

# Filter by type
python3 /opt/zend/services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 10
```

## Recovery

### State is Corrupted

```bash
# Stop daemon
sudo systemctl stop zend-daemon

# Backup old state
mv /opt/zend/state /opt/zend/state.backup

# Create fresh state
mkdir /opt/zend/state

# Restart daemon (will create new principal)
sudo systemctl start zend-daemon

# Re-pair devices
python3 /opt/zend/services/home-miner-daemon/cli.py pair --device alice-phone --capabilities observe,control
```

### Daemon Won't Start

Check logs:
```bash
sudo journalctl -u zend-daemon -f
```

Common issues:
- Port already in use: `lsof -i :8080` to find conflicting process
- Permission denied: Ensure user has write access to state directory
- Python version: Verify `python3 --version` is 3.10+

### Pairing Token Expired

If you see "unauthorized" errors:

```bash
# Refresh pairing (invalidate old token, create new)
python3 /opt/zend/services/home-miner-daemon/cli.py pair --device alice-phone --capabilities observe,control
```

### Phone Can't Connect

1. Verify server is running: `curl http://localhost:8080/health`
2. Check firewall: `sudo ufw status` (allow port 8080 if needed)
3. Verify LAN connectivity: ping server from phone
4. Check API_BASE URL in index.html matches server IP

## Maintenance

### View Logs

Systemd logs:
```bash
sudo journalctl -u zend-daemon -n 100 --no-pager
```

### Restart After Updates

```bash
cd /opt/zend
git pull

sudo systemctl restart zend-daemon
```

### Backup State

```bash
# Create backup
sudo systemctl stop zend-daemon
tar -czf zend-backup-$(date +%Y%m%d).tar.gz /opt/zend/state
sudo systemctl start zend-daemon

# Restore from backup
sudo systemctl stop zend-daemon
tar -xzf zend-backup-20260322.tar.gz -C /
sudo systemctl start zend-daemon
```

## Monitoring

### Health Check Script

Create `/opt/zend/scripts/monitor.sh`:

```bash
#!/bin/bash
RESPONSE=$(curl -s http://127.0.0.1:8080/health)
if echo "$RESPONSE" | grep -q '"healthy": true'; then
    echo "OK: Daemon healthy"
    exit 0
else
    echo "WARN: $RESPONSE"
    exit 1
fi
```

### Add to Cron

```bash
# Check every 5 minutes
*/5 * * * * /opt/zend/scripts/monitor.sh >> /var/log/zend-monitor.log 2>&1
```

## Troubleshooting

### curl: (7) Failed to connect

- Daemon not running: `sudo systemctl start zend-daemon`
- Wrong IP/port: Verify server address
- Firewall blocking: Check ufw rules

### {"error": "unauthorized"}

- Device not paired: Run `pair` command
- Capability missing: Re-pair with required capabilities
- Token expired: Re-pair device

### index.html Shows "Unable to Connect"

- Daemon not running: Start with `./scripts/bootstrap_home_miner.sh`
- Wrong API_BASE: Update IP address in the HTML file
- CORS issue: Currently not supported for cross-origin requests

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop zend-daemon
sudo systemctl disable zend-daemon

# Remove service file
sudo rm /etc/systemd/system/zend-daemon.service
sudo systemctl daemon-reload

# Remove application files
sudo rm -rf /opt/zend

# Optional: Remove state (WARNING: loses all data)
sudo rm -rf /opt/zend/state
```
