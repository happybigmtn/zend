# Operator Quickstart

This guide helps you deploy the Zend Home Miner daemon on home hardware. You don't need cloud infrastructure or containers—just a Linux machine with Python.

## Hardware Requirements

- **CPU**: Any modern x86_64 or ARM processor
- **RAM**: 256 MB minimum
- **Storage**: 100 MB for code, state grows slowly
- **OS**: Linux (tested on Debian, Ubuntu, Raspberry Pi OS)
- **Network**: Ethernet or WiFi (daemon binds to LAN)

### Tested Platforms

- Raspberry Pi 4 (ARM64)
- Raspberry Pi 3 (ARM32)
- x86_64 virtual machines
- Any Linux machine with Python 3.10+

## Installation

### 1. Get the code

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

Or download and extract the release archive:

```bash
curl -L https://example.com/zend.tar.gz | tar xz
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or higher
```

If not, install Python 3.10+:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install python3
```

### 3. Create a dedicated user (recommended)

```bash
sudo useradd -r -s /bin/false zend || true
sudo chown -R zend:zend /opt/zend
```

## Configuration

Set these environment variables before starting:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface. Use `0.0.0.0` for LAN access |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `./state` | Where to store identity and events |

### Configure for LAN access

To control the miner from devices on your network:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=/opt/zend/state
```

For persistent configuration, add to `/etc/environment` or create a systemd override:

```bash
sudo mkdir -p /etc/systemd/system/zend.service.d
sudo tee /etc/systemd/system/zend.service.d/override.conf <<EOF
[Service]
Environment=ZEND_BIND_HOST=0.0.0.0
Environment=ZEND_BIND_PORT=8080
Environment=ZEND_STATE_DIR=/opt/zend/state
EOF
```

## First Boot

### 1. Bootstrap the daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1234)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### 2. Verify the daemon is running

```bash
curl http://127.0.0.1:8080/health
```

Expected response:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 12}
```

### 3. Check miner status

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
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

## Pairing a Phone

### On the home server

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

Expected output:

```
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
paired alice-phone
capability=observe,control
```

### Capability levels

| Capability | What it allows |
|------------|----------------|
| `observe` | View miner status, temperature, mode, events |
| `control` | Start/stop mining, change mode |

Pair devices with only `observe` if you want a read-only display:

```bash
./scripts/pair_gateway_client.sh --client kitchen-display --capabilities observe
```

## Opening the Command Center

### Option 1: Direct file access

Copy `apps/zend-home-gateway/index.html` to your phone:

```bash
# On the server, serve the file
cd apps/zend-home-gateway
python3 -m http.server 8081
```

Then on your phone, open `http://<server-ip>:8081/index.html`.

### Option 2: Local file (file://)

Transfer `index.html` to your phone and open it directly. The JavaScript connects to `http://127.0.0.1:8080` by default, which works if you're on the same machine.

### Option 3: LAN access

Configure the daemon to bind to `0.0.0.0`:

```bash
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

Then open `apps/zend-home-gateway/index.html` in your phone's browser and modify the `API_BASE` constant if needed:

```javascript
const API_BASE = 'http://192.168.1.100:8080';  // Your server IP
```

## Daily Operations

### Check daemon status

```bash
curl http://127.0.0.1:8080/health
```

### Check miner status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Start mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

### Stop mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### Change mining mode

```bash
# Pause all mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode paused

# Balanced (50 kH/s)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Performance (150 kH/s)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode performance
```

### View event history

```bash
python3 services/home-miner-daemon/cli.py events --limit 50
```

### List paired devices

```bash
cat state/pairing-store.json | python3 -m json.tool
```

## Systemd Service (Recommended)

Create a systemd service for automatic startup:

```bash
sudo tee /etc/systemd/system/zend.service <<EOF
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=zend
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Environment=ZEND_BIND_HOST=127.0.0.1
Environment=ZEND_BIND_PORT=8080
Environment=ZEND_STATE_DIR=/opt/zend/state
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend
sudo systemctl status zend
```

## Recovery

### Daemon won't start

Check logs:

```bash
journalctl -u zend -n 50
```

Common causes:

1. **Port already in use**: Kill the old process or change `ZEND_BIND_PORT`
2. **Permission denied**: Ensure state directory is writable by the daemon user
3. **Python version**: Verify `python3 --version` is 3.10+

### State is corrupted

Reset state files:

```bash
systemctl stop zend
rm -rf /opt/zend/state
systemctl start zend
./scripts/bootstrap_home_miner.sh
```

Warning: This creates a new principal identity. Paired devices will need to re-pair.

### Can't connect from phone

1. Verify daemon is running: `curl http://127.0.0.1:8080/health`
2. If using LAN, verify `ZEND_BIND_HOST=0.0.0.0`
3. Check firewall: `sudo ufw allow 8080/tcp`
4. Verify phone is on the same network

### Pairing failed

```bash
# Check existing pairings
cat state/pairing-store.json

# Remove a stale pairing
python3 -c "
import json
with open('state/pairing-store.json') as f:
    data = json.load(f)
# Remove by device name
new_data = {k: v for k, v in data.items() if v['device_name'] != 'old-device'}
with open('state/pairing-store.json', 'w') as f:
    json.dump(new_data, f)
"
```

## Security

### LAN-only by default

The daemon binds to `127.0.0.1` by default, accessible only from the local machine. This prevents accidental internet exposure.

### When enabling LAN access

Only expose on trusted networks. The daemon has:

- No authentication by default (relies on LAN isolation)
- No TLS (use VPN or SSH tunnel for remote access)
- No rate limiting

### For remote access (advanced)

Use an SSH tunnel instead of exposing the daemon directly:

```bash
# On your phone/laptop
ssh -L 8080:127.0.0.1:8080 user@home-server
```

Then connect to `http://127.0.0.1:8080` as usual.

### Revoking device access

Remove the pairing record:

```bash
rm state/pairing-store.json
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

## Logs

### Daemon logs (systemd)

```bash
journalctl -u zend -f
```

### Event spine

The event spine logs all operations to `state/event-spine.jsonl`:

```bash
tail -f state/event-spine.jsonl
```

### View recent events

```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

## Updating

```bash
cd /opt/zend
git pull
systemctl restart zend
```

Review the changelog and test in a non-production environment first.

## Uninstalling

```bash
systemctl stop zend
systemctl disable zend
rm /etc/systemd/system/zend.service
rm -rf /opt/zend
```

Optionally remove state data:

```bash
rm -rf /opt/zend/state
```
