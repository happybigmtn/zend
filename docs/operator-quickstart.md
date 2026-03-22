# Operator Quickstart

This guide walks you through deploying Zend on home hardware. By the end, you'll
have a running daemon, a paired phone, and a working command center accessible
from your browser.

## Hardware Requirements

- Any Linux machine with Python 3.10+ (Raspberry Pi, old laptop, mini PC, NAS)
- 512 MB RAM minimum
- 1 GB disk space
- Local network access (WiFi or Ethernet)

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> && cd zend
```

### 2. Verify Python

```bash
python3 --version  # Must be 3.10 or higher
```

No pip install needed. Zend uses only the Python standard library.

## Configuration

### Environment Variables

Set these before running the daemon:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_STATE_DIR` | `./state/` | State file directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI tools |

For LAN access (access from other devices on your network):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=/home/youruser/zend/state
```

For development (local only, default):

```bash
export ZEND_BIND_HOST=127.0.0.1
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=./state
```

### State Directory

Create the state directory:

```bash
mkdir -p state
```

The daemon stores pairing records, principal identity, and the event spine here.
This directory is automatically created if it doesn't exist.

## First Boot

### 1. Bootstrap the Daemon

```bash
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

The daemon is now running. Take note of the `principal_id` — this is your
Zend identity.

### 2. Verify the Daemon

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Open the Command Center

On the machine running the daemon, open this file in your browser:

```
apps/zend-home-gateway/index.html
```

If you're on a different machine, you need to bind to LAN first (see below).

## Pairing a Phone

### For LAN Access

If you want to access the daemon from your phone, bind it to all interfaces:

```bash
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

Then find your machine's LAN IP address:

```bash
# On Linux
ip addr show | grep "inet "

# On macOS
ifconfig | grep "inet "

# On Windows
ipconfig
```

Look for an address like `192.168.1.100` or `10.0.0.50`.

### Pair a New Device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

This creates a pairing record with both `observe` and `control` capabilities.

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:00:00Z"
}

paired my-phone
capability=observe,control
```

### Access from Phone Browser

The daemon does not serve static files. To access the gateway from your phone,
serve the HTML file with Python's built-in HTTP server:

```bash
cd apps/zend-home-gateway
python3 -m http.server 8081 --bind 0.0.0.0 &
```

Then on your phone, open:

```
http://192.168.1.100:8081/index.html
```

Replace `192.168.1.100` with your machine's LAN IP address.

**Note:** The gateway HTML has `API_BASE` hardcoded to `http://127.0.0.1:8080`.
For phone access, edit line 632 of `index.html` to use your machine's LAN IP:

```javascript
const API_BASE = 'http://192.168.1.100:8080';
```

## Daily Operations

### Check Status

```bash
./scripts/read_miner_status.sh --client my-phone
```

Expected output:
```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:05:00Z"
}

status=MinerStatus.STOPPED
mode=MinerMode.PAUSED
freshness=2026-03-22T10:05:00Z
```

### Start Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action start
```

Expected output:
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}

acknowledged=true
note='Action accepted by home miner, not client device'
```

### Change Mining Mode

```bash
# Balanced mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Performance mode
./scripts/set_mining_mode.sh --client my-phone --mode performance

# Paused (no mining)
./scripts/set_mining_mode.sh --client my-phone --mode paused
```

### Stop Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action stop
```

### View Events (Operations Inbox)

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Only control receipts
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Only pairing events
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
```

### List Paired Devices

```bash
cat state/pairing-store.json | python3 -m json.tool
```

## Recovery

### Daemon Won't Start (Port Already in Use)

```bash
# Find and kill the process using the port
lsof -i :8080
kill <PID>

# Or use the built-in stop
./scripts/bootstrap_home_miner.sh --stop
```

### Corrupted State

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove state files (this resets everything)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

**Note:** The bootstrap is idempotent for the daemon but NOT for pairing. If you
bootstrap twice with the same device name, the second run fails because
`pair_client()` rejects duplicate device names. Always `rm -rf state/*` before
re-bootstrapping, or use a different device name.

### Daemon Crashed

```bash
# Check if it's still running
ps aux | grep daemon.py

# Restart
./scripts/bootstrap_home_miner.sh --daemon
```

### Event Spine Corruption

If `state/event-spine.jsonl` is corrupted:

```bash
# Backup the corrupted file
mv state/event-spine.jsonl state/event-spine.jsonl.bak

# Create a new spine
touch state/event-spine.jsonl

# Note: This loses event history. For production, implement backups.
```

## Security

### LAN-Only Binding

By default, the daemon binds to `127.0.0.1`, which means only processes on the
same machine can access it. This is the safest default.

To allow access from other devices on your network:

```bash
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### What to Check

- [ ] Firewall allows access to `ZEND_BIND_PORT` on your local network
- [ ] You're not exposing the daemon to the internet (check with `curl ifconfig.me`)
- [ ] State directory has appropriate permissions (`chmod 700 state`)

### What Not to Expose

- [ ] Do not expose port 8080 to the internet
- [ ] Do not run the daemon as root
- [ ] Do not store sensitive data in the state directory without encryption

## Service Setup (Systemd)

For persistent operation, create a systemd service:

```ini
# /etc/systemd/system/zend-daemon.service
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/home/youruser/zend/state"
ExecStart=/usr/bin/python3 /home/youruser/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-daemon
sudo systemctl start zend-daemon

# Check status
sudo systemctl status zend-daemon
```

## Troubleshooting

### "curl: (7) Failed to connect to 127.0.0.1 port 8080"

The daemon isn't running. Start it:

```bash
./scripts/bootstrap_home_miner.sh --daemon
```

### "Error: Client lacks 'control' capability"

The paired device only has `observe` capability. Pair again with control:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### "Error: daemon_unavailable"

The daemon isn't responding. Check if it's running:

```bash
ps aux | grep daemon.py
curl http://127.0.0.1:8080/health
```

### Phone Can't Connect to Daemon

1. Ensure daemon is bound to `0.0.0.0` (not `127.0.0.1`)
2. Check firewall: `sudo ufw allow 8080`
3. Verify LAN IP: `ip addr show | grep "inet "`
4. Use the LAN IP in the browser: `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`

### High CPU Usage

The miner simulator shouldn't use significant CPU. If it does:

```bash
# Check what's running
ps aux | grep python

# Restart the daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

## Performance Expectations

- Daemon startup: < 2 seconds
- Status check: < 100ms response
- Mode change: < 200ms acknowledgment
- Memory usage: < 50 MB
- Disk usage: < 10 MB for state files

## Next Steps

- Read [docs/architecture.md](architecture.md) to understand the system design
- Read [docs/api-reference.md](api-reference.md) for all available endpoints
- Explore [specs/](specs/) to understand the product direction
- Check [plans/](plans/) for upcoming features
