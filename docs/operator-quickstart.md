# Operator Quickstart

This guide covers deploying Zend on home hardware—from initial setup to daily operations.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86-64 or ARM | ARMv8+ (Raspberry Pi 4+) |
| RAM | 256 MB | 512 MB+ |
| Storage | 100 MB | 1 GB+ |
| OS | Linux, macOS, WSL | Linux (Raspberry Pi OS, Ubuntu) |
| Network | Ethernet or WiFi | Ethernet for stability |
| Python | 3.10+ | 3.10+ |

Zend runs on Raspberry Pi, old laptops, mini PCs, or any Linux machine you have running 24/7.

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

### 3. Make Scripts Executable

```bash
chmod +x scripts/*.sh
```

## Configuration

The daemon accepts environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `$(pwd)/state` | Where to store state files |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

### LAN Access Configuration

To access Zend from devices on your network:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

**Warning**: Binding to `0.0.0.0` exposes the daemon on your local network. Only do this on trusted networks.

For better security, bind to your specific LAN interface:

```bash
# Find your LAN IP
ip addr show | grep inet

# Bind to that IP
export ZEND_BIND_HOST=192.168.1.100
```

## First Boot

### 1. Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon started (PID: 12345)
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "capabilities": ["observe"]
}
```

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
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
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

## Pairing a Phone

### From the Command Line

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### From the CLI

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

Expected:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
```

### Accessing the Command Center

1. Transfer `apps/zend-home-gateway/index.html` to your phone, or
2. Serve it from the machine running the daemon:

```bash
# On the daemon machine
cd apps/zend-home-gateway
python3 -m http.server 8081

# Access from phone browser
# http://<daemon-machine-ip>:8081/index.html
```

3. The command center auto-connects to `http://127.0.0.1:8080`. Update the `API_BASE` variable if using a different URL.

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt

# Last 20 events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode performance
```

## Mining Modes

| Mode | Hashrate | Use Case |
|------|----------|----------|
| `paused` | 0 H/s | Off, testing, maintenance |
| `balanced` | 50 kH/s | Normal daily operation |
| `performance` | 150 kH/s | Maximum power, higher energy use |

## Recovery

### Daemon Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Stop any existing process
./scripts/bootstrap_home_miner.sh --stop

# Clear stale state
rm -rf state/*

# Restart
./scripts/bootstrap_home_miner.sh
```

### State Corruption

If pairing or principal state is corrupted:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

This creates fresh principal and pairing data.

### Event Spine Recovery

Events are append-only and stored in `state/event-spine.jsonl`. If corrupted:

```bash
# View recent events
tail -n 100 state/event-spine.jsonl

# Reset spine (loses all events)
rm state/event-spine.jsonl
```

### Port Conflicts

If `8080` is in use:

```bash
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

Update CLI calls to use the new port:
```bash
export ZEND_DAEMON_URL=http://127.0.0.1:8081
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
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
sudo systemctl enable zend-home
sudo systemctl start zend-home

# Check status
sudo systemctl status zend-home

# View logs
journalctl -u zend-home -f
```

### Launchd (macOS)

Create `~/Library/LaunchAgents/com.zend.home.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zend.home</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/opt/zend/services/home-miner-daemon/daemon.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ZEND_BIND_HOST</key>
        <string>127.0.0.1</string>
        <key>ZEND_BIND_PORT</key>
        <string>8080</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>/opt/zend</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.zend.home.plist
launchctl start com.zend.home
```

## Security Considerations

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. It is only accessible from the local machine.

### When Exposing on LAN

1. Only do this on trusted home networks
2. Prefer binding to a specific IP rather than `0.0.0.0`
3. Consider firewall rules to block external access
4. The daemon has no authentication in milestone 1—anyone on the network can control mining

### Firewalld (Linux)

```bash
# Allow local network access
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### ufw (Ubuntu/Debian)

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

## Troubleshooting

### Cannot Connect from Phone

1. Verify daemon is running:
   ```bash
   curl http://127.0.0.1:8080/health
   ```

2. Check if binding to LAN:
   ```bash
   # Should show 0.0.0.0 or your LAN IP
   grep BIND services/home-miner-daemon/daemon.py
   ```

3. Check firewall:
   ```bash
   sudo iptables -L -n | grep 8080
   ```

### Control Actions Fail

1. Verify device has `control` capability:
   ```bash
   python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted
   ```

2. Check for control receipt:
   ```bash
   python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 5
   ```

### Status Shows Stale

If status shows `freshness` as old:

1. Daemon may be crashed:
   ```bash
   ./scripts/bootstrap_home_miner.sh --status
   ```

2. Restart daemon:
   ```bash
   ./scripts/bootstrap_home_miner.sh --stop
   ./scripts/bootstrap_home_miner.sh
   ```

## Maintenance

### Update Zend

```bash
cd /opt/zend
git pull
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Backup State

```bash
tar -czf zend-backup-$(date +%Y%m%d).tar.gz state/
```

### Monitor Logs

If running as a service:

```bash
# systemd
journalctl -u zend-home -f

# Direct
python3 services/home-miner-daemon/daemon.py 2>&1 | tee daemon.log
```
