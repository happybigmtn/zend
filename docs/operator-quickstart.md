# Operator Quickstart

Deploy Zend on home hardware. This guide assumes you have a Linux machine (Raspberry Pi, home server, NAS) with Python 3.10+.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any 64-bit ARM or x86 | ARMv8+ or modern x86 |
| RAM | 512 MB | 1 GB |
| Storage | 100 MB | 1 GB |
| Network | Ethernet or WiFi | Ethernet |
| OS | Linux (any distro) | Raspberry Pi OS, Ubuntu Server |

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> ~/zend
cd ~/zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or higher
```

### 3. Create State Directory

```bash
mkdir -p ~/zend/state
chmod 700 ~/zend/state
```

The `state/` directory stores:
- `principal.json`: Your identity
- `pairing-store.json`: Paired devices
- `event-spine.jsonl`: Operational log
- `daemon.pid`: Daemon process ID

## Configuration

Set environment variables before starting:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `$(pwd)/state` | Where to store runtime data |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

### LAN Access (Phone on Same Network)

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

**Warning**: Binding to `0.0.0.0` exposes the control surface on your LAN. Only do this if your LAN is trusted.

### Production (Single Machine)

```bash
export ZEND_BIND_HOST=127.0.0.1
export ZEND_BIND_PORT=8080
```

## First Boot

### 1. Start the Daemon

```bash
cd ~/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Check Status

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
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

## Pairing a Phone

### 1. Find Your Machine's LAN IP

```bash
hostname -I | awk '{print $1}'
```

Example: `192.168.1.100`

### 2. Configure Daemon for LAN

```bash
# Stop existing daemon
./scripts/bootstrap_home_miner.sh --stop

# Start with LAN binding
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh
```

### 3. Open Command Center on Phone

1. Connect phone to same WiFi/LAN
2. Open browser
3. Navigate to: `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`

The HTML file is self-contained. It will connect to the daemon API at the same host.

### 4. Verify Connection

The status hero should show "stopped" or "running" with a freshness timestamp.

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode performance
```

### Start/Stop Mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action stop
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --limit 10

# Only control receipts
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

## Recovery

### State Corruption

If the daemon fails to start or behaves incorrectly:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state (keeps scripts intact)
rm -rf ~/zend/state/*

# Restart
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

1. Check port availability:
   ```bash
   lsof -i :8080
   ```

2. If port is in use, kill the process or change `ZEND_BIND_PORT`

3. Restart:
   ```bash
   ./scripts/bootstrap_home_miner.sh
   ```

### Phone Can't Connect

1. Verify daemon is running:
   ```bash
   curl http://<your-ip>:8080/health
   ```

2. Check firewall:
   ```bash
   # Allow port 8080
   sudo ufw allow 8080/tcp
   ```

3. Verify phone is on same network

## Security

### LAN-Only Default

Zend binds to `127.0.0.1` by default. This means only processes on the same machine can access the control surface.

### Exposing on LAN

Only expose on LAN if:
- Your network is trusted (home network, not public WiFi)
- You understand that any device on LAN can access the daemon
- You're okay with any paired device issuing control commands

### What Not to Expose

- **Never** expose the daemon to the public internet
- **Never** bind to `0.0.0.0` on a VPS or cloud machine
- **Never** skip the pairing step in production

### Pairing Security

- Each device needs explicit pairing
- Pairing records store capability scopes
- `observe` can read status only
- `control` can change modes and start/stop

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or find and kill manually:

```bash
kill $(cat ~/zend/state/daemon.pid)
```

## Automation (systemd)

To run as a service:

```bash
# /etc/systemd/system/zend.service
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
Environment="ZEND_BIND_HOST=127.0.0.1"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/usr/bin/python3 /home/pi/zend/services/home-miner-daemon/daemon.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend
sudo systemctl start zend
```
