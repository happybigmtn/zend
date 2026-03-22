# Operator Quickstart

This guide walks you through deploying Zend on home hardware—a Raspberry Pi, old laptop, or any Linux box.

## Hardware Requirements

- Linux (Raspberry Pi OS, Ubuntu, Debian, etc.)
- Python 3.10 or higher
- Network access (same LAN as your phone)
- 100MB disk space

No GPU required for milestone 1 (uses a simulator).

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or higher
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind to `0.0.0.0` for LAN access |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory |

### Recommended Production Settings

For LAN access (your phone on the same network):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=/var/lib/zend/state
```

Or add to your shell profile:

```bash
echo 'export ZEND_BIND_HOST=0.0.0.0' >> ~/.bashrc
echo 'export ZEND_BIND_PORT=8080' >> ~/.bashrc
source ~/.bashrc
```

## First Boot

### 1. Bootstrap the System

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
  "paired_at": "2026-03-22T18:30:00.000000+00:00"
}
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 10}
```

### 3. Grant Control Capability (Optional)

By default, devices get `observe` only. To enable control:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone \
  --capabilities observe,control
```

## Pairing Your Phone

### 1. Find Your Server's IP

```bash
hostname -I
# Example: 192.168.1.100
```

### 2. Configure Daemon for LAN Access

If not already set:

```bash
export ZEND_BIND_HOST=0.0.0.0
# Restart daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### 3. Access the Command Center

On your phone, open:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

Or serve the HTML file directly:

```bash
cd apps/zend-home-gateway
python3 -m http.server 8080
# Open http://192.168.1.100:8080/index.html on phone
```

## Daily Operations

### Check Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Via HTTP
curl http://127.0.0.1:8080/status
```

### Start/Stop Mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop
```

### Change Mining Mode

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

Modes:
- `paused`: Mining disabled
- `balanced`: Moderate hashrate (~50 kH/s)
- `performance`: Maximum hashrate (~150 kH/s)

### View Event Log

```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone \
  --limit 20
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Running as a Service (systemd)

Create a service file:

```bash
sudo nano /etc/systemd/system/zend.service
```

```
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
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

Check logs:

```bash
sudo journalctl -u zend -f
```

## Recovery

### State Corruption

If the daemon won't start or reports errors:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup corrupted state
mv state state.backup

# Fresh bootstrap
./scripts/bootstrap_home_miner.sh

# Note: You'll need to re-pair your devices
```

### Daemon Won't Start (Port in Use)

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process or change ZEND_BIND_PORT
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Verify Pairing Store

```bash
cat state/pairing-store.json
```

### View Event Spine

```bash
tail -20 state/event-spine.jsonl
```

## Security

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. This means:
- Only processes on the same machine can access it
- No firewall configuration needed for local use

### Exposing Beyond LAN

Setting `ZEND_BIND_HOST=0.0.0.0` exposes the daemon on your local network:

**Do:**
- Keep your router's firewall enabled
- Don't forward port 8080 to the internet
- Use only on trusted networks

**Don't:**
- Expose the daemon publicly
- Trust requests from unknown devices
- Skip authentication checks (future feature)

### Current Limitations

- No TLS/HTTPS in milestone 1
- No per-request authentication
- No rate limiting

## Troubleshooting

### Phone can't reach daemon

1. Verify daemon is running:
   ```bash
   curl http://127.0.0.1:8080/health
   ```

2. Check firewall:
   ```bash
   sudo ufw allow 8080/tcp
   ```

3. Verify IP address:
   ```bash
   hostname -I
   ```

### Command center shows "Unable to connect"

1. Ensure daemon is running
2. Check the API base URL in the HTML (change `127.0.0.1` to server IP)
3. Try refreshing the page

### Control commands fail

1. Check device capabilities:
   ```bash
   cat state/pairing-store.json
   ```

2. Verify device has `control` capability
3. Re-pair if needed

## Quick Reference

```bash
# Start
./scripts/bootstrap_home_miner.sh

# Status
python3 services/home-miner-daemon/cli.py health
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# View logs
tail -f state/event-spine.jsonl
```
