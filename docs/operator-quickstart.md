# Operator Quickstart

This guide helps operators deploy the Zend Home Miner Daemon on home hardware (Raspberry Pi, home server, NAS, etc.).

## Overview

Zend runs a local daemon that pairs with your phone to control a home miner. The daemon:

- Runs entirely on your local network
- Uses Python stdlib only (no pip install)
- Binds to a private interface only
- Stores state locally in JSON files

## Hardware Requirements

### Minimum

- Any Linux system (Raspberry Pi OS, Ubuntu, Debian, etc.)
- Python 3.10 or higher
- 100 MB disk space
- Network access to your phone

### Recommended

- Raspberry Pi 4 or newer
- 4 GB RAM
- 16 GB SD card
- Ethernet connection for stability

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> zend
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or higher
```

No pip install needed — the daemon uses Python stdlib only.

## Configuration

The daemon respects these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `$(pwd)/state` | Where to store state files |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind to |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Pairing token lifetime |

### LAN Configuration

To allow your phone to connect over LAN:

```bash
# Find your LAN interface IP
ip addr show | grep inet

# Example output: inet 192.168.1.100/24

# Start daemon with LAN binding
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

**Security Note**: Only bind to private network interfaces (192.168.x.x, 10.x.x.x, etc.). Never bind to `0.0.0.0` or a public IP.

## First Boot

### 1. Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Stopping daemon (PID: 1234)
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00Z"
}
[INFO] Bootstrap complete
```

### 2. Pair Your Phone

The default bootstrap creates a pairing for `alice-phone` with `observe` capability. To pair with control capability:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
```

### 3. Access the Command Center

1. Connect your phone to the same LAN
2. Open `apps/zend-home-gateway/index.html` in your phone's browser
3. The UI will connect to the daemon at `http://192.168.1.100:8080`

**Note**: For the HTML file to connect, you may need to serve it via HTTP:

```bash
# On the daemon host
cd apps/zend-home-gateway
python3 -m http.server 8081

# On your phone, visit:
# http://192.168.1.100:8081/index.html
```

### 4. Verify Connection

In the command center UI, you should see:
- Miner status (running/stopped)
- Current mode (paused/balanced/performance)
- Hashrate
- Last updated timestamp

## Daily Operations

### Check Status

```bash
# CLI
python3 services/home-miner-daemon/cli.py status

# curl
curl http://localhost:8080/status
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode performance
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Specific event kinds
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### Health Check

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

## Recovery

### Daemon Won't Start

1. Check if another process is using the port:
   ```bash
   lsof -i :8080
   ```

2. Stop any existing daemon:
   ```bash
   ./scripts/bootstrap_home_miner.sh --stop
   ```

3. Clear corrupted state:
   ```bash
   rm -rf state/*
   ./scripts/bootstrap_home_miner.sh
   ```

### State is Corrupted

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup old state (optional)
mv state state.backup

# Clear and re-bootstrap
rm -rf state
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Connect

1. Verify phone and daemon are on same network:
   ```bash
   ping 192.168.1.100
   ```

2. Check firewall rules:
   ```bash
   # Allow incoming on the daemon port (example for ufw)
   sudo ufw allow 8080/tcp
   ```

3. Verify daemon is running:
   ```bash
   ./scripts/bootstrap_home_miner.sh --status
   ```

### Re-pair a Device

```bash
# Remove existing pairing
# Edit state/pairing-store.json to remove the device entry

# Re-pair
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
```

## Security

### LAN-Only By Design

The daemon is designed for LAN-only operation in milestone 1:

- Binds to private interface by default
- No TLS/SSL (local network assumed trusted)
- No authentication beyond device pairing

### Hardening Checklist

- [ ] Bind to specific LAN IP, not `0.0.0.0`
- [ ] Use firewall to block WAN access to daemon port
- [ ] Don't expose state files to other users
- [ ] Regularly update the system
- [ ] Review pairing store for unauthorized devices

### What NOT to Do

- Don't expose the daemon port to the internet
- Don't bind to `0.0.0.0` on a multi-homed host
- Don't share state files without encryption
- Don't skip the firewall

## Service Management

### Run as Systemd Service

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/home/pi/zend/scripts/bootstrap_home_miner.sh --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend
sudo systemctl start zend

# Check status
sudo systemctl status zend
```

### Run at Startup

Alternatively, add to crontab:

```bash
crontab -e

# Add line:
@reboot cd /home/pi/zend && ./scripts/bootstrap_home_miner.sh >> /home/pi/zend/state/daemon.log 2>&1
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Daemon won't start | Check port availability, run `--stop` first |
| Phone can't reach daemon | Verify LAN connectivity, check firewall |
| Status shows stale | Daemon may have crashed, restart with `--stop` then bootstrap |
| Pairing fails | Check pairing-store.json for duplicates |
| No events showing | Events may be in different file, check state/ directory |

## State Files

The daemon creates these files in `state/`:

| File | Purpose |
|------|---------|
| `principal.json` | Your Zend identity |
| `pairing-store.json` | Paired devices and capabilities |
| `event-spine.jsonl` | All operational events |
| `daemon.pid` | Running daemon process ID |

State files are disposable. Delete them to re-bootstrap from scratch.

## Next Steps

- Read the [API Reference](api-reference.md) for programmatic access
- Read the [Architecture](architecture.md) for system design
- Check [plans/](../plans/) for upcoming features
