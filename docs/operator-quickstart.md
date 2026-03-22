# Operator Quickstart

Deploy Zend on home hardware. This guide assumes you have a Linux machine
(Raspberry Pi, NAS, server, or desktop) on your local network.

## Hardware Requirements

- Linux system (Raspberry Pi OS, Ubuntu, Debian, etc.)
- Python 3.10 or later
- Local network access
- 100 MB disk space

No special hardware needed. The miner simulator runs on any Python-capable device.

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> ~/zend
cd ~/zend
```

### 2. Verify Python Version

```bash
python3 --version  # Must be 3.10 or later
```

If not, install Python 3.10+:

```bash
# Raspberry Pi / Debian / Ubuntu
sudo apt update && sudo apt install python3 python3-venv
```

## Configuration

Set environment variables to customize the deployment:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Network interface to bind |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `state/` | Where to store state |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

For LAN access (default recommended):

```bash
export ZEND_BIND_HOST="0.0.0.0"        # Bind to all interfaces
export ZEND_BIND_PORT="8080"
export ZEND_STATE_DIR="$HOME/zend-state"
```

For localhost-only (development):

```bash
export ZEND_BIND_HOST="127.0.0.1"
export ZEND_BIND_PORT="8080"
```

## First Boot

### Start the Daemon

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
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

### Verify Health

```bash
curl http://localhost:8080/health
```

Expected output:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

## Pairing a Phone

### 1. Find the Daemon IP

On the daemon machine:

```bash
hostname -I | awk '{print $1}'
```

Note the IP address (e.g., `192.168.1.100`).

### 2. Update CLI URL

On your phone or another machine on the same network:

```bash
export ZEND_DAEMON_URL="http://192.168.1.100:8080"
```

### 3. Pair a New Client

```bash
python3 services/home-miner-daemon/cli.py pair \
    --device my-phone \
    --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:05:00Z"
}
```

## Opening the Command Center

The command center is a single HTML file. Access it from your phone's browser:

```
file://<path-to-repo>/apps/zend-home-gateway/index.html
```

For network access, copy the file to your phone or serve it:

```bash
# Option 1: Copy file to phone via scp/smb
scp apps/zend-home-gateway/index.html phone@192.168.1.50:~/Downloads/

# Option 2: Serve locally (requires Python on phone)
cd apps/zend-home-gateway
python3 -m http.server 8081
# Then open http://<your-ip>:8081/index.html on phone
```

**Note:** The command center connects to `http://127.0.0.1:8080` by default.
Update the `API_BASE` variable in the HTML file if accessing remotely:

```javascript
const API_BASE = 'http://192.168.1.100:8080';
```

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Start/Stop Mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
    --client my-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
    --client my-phone --action stop
```

### Change Mode

```bash
python3 services/home-miner-daemon/cli.py control \
    --client my-phone --action set_mode --mode balanced
```

Modes:
- `paused`: No mining
- `balanced`: 50 kH/s
- `performance`: 150 kH/s

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events \
    --client my-phone --kind control_receipt

# Limit to 5 events
python3 services/home-miner-daemon/cli.py events \
    --client my-phone --limit 5
```

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or kill by PID:

```bash
kill $(cat state/daemon.pid)
```

## Recovery

### State Corruption

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start (Port in Use)

```bash
# Find what's using the port
lsof -i :8080

# Kill it or use a different port
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Complete Reset

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
git pull  # Get latest code
./scripts/bootstrap_home_miner.sh
```

## Security

### LAN-Only by Default

The daemon binds to your local network only. It does not expose any internet
control surfaces.

### What to Check

- [ ] Daemon binds to private IP (192.168.x.x, 10.x.x.x, etc.), not 0.0.0.0 on internet-facing machines
- [ ] Firewall blocks port 8080 from the internet
- [ ] No sensitive data in `state/` directory (it contains your principal ID)

### What Not to Expose

- [ ] Do not port-forward 8080 to the internet
- [ ] Do not run the daemon as root unnecessarily
- [ ] Do not share the pairing token publicly

### Firewall Setup

```bash
# Allow local network access
sudo ufw allow from 192.168.0.0/16 to any port 8080

# Block internet access (if ufw enabled)
sudo ufw deny 8080
```

## Running on Raspberry Pi

```bash
# Install Python if needed
sudo apt update && sudo apt install python3 python3-venv

# Clone and setup
git clone <repo-url> ~/zend
cd ~/zend

# Start with LAN binding
export ZEND_BIND_HOST="0.0.0.0"
./scripts/bootstrap_home_miner.sh

# Find Pi's IP
hostname -I | awk '{print $1}'
```

Access the command center from your phone using the Pi's IP address.

## Auto-Start on Boot (systemd)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/zend.service
```

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/home/pi/zend/scripts/bootstrap_home_miner.sh
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

## Monitoring

### View Logs

The daemon doesn't write logs to a file by default. To capture logs:

```bash
# Redirect output to file
./scripts/bootstrap_home_miner.sh 2>&1 | tee -a ~/zend.log
```

### Check Daemon Health

```bash
watch -n 5 'curl -s http://localhost:8080/health'
```

### Monitor Events

```bash
watch -n 10 'python3 services/home-miner-daemon/cli.py events --client my-phone'
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Unable to connect to Zend Home" | Check daemon is running: `curl http://localhost:8080/health` |
| "This device lacks 'control' capability" | Re-pair with control capability: `--capabilities observe,control` |
| "Daemon failed to start" | Check port: `lsof -i :8080` or use different port |
| "Showing cached status" | Daemon may be offline, check health endpoint |
| HTML page shows no data | Update `API_BASE` in the HTML file to daemon's IP |

## Next Steps

- Read `docs/architecture.md` for system design details
- Read `docs/api-reference.md` for all API endpoints
- Explore `references/` for architecture contracts
