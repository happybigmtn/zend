# Operator Quickstart

This guide walks you through deploying Zend on home hardware. You'll run the daemon locally, pair your phone, and access the command center.

## Hardware Requirements

- Any Linux machine (Raspberry Pi, old laptop, NAS, etc.)
- Python 3.10 or higher
- Network access (phone and daemon must be on same LAN)

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

No pip install needed. Zend uses Python stdlib only.

## Configuration

Set these environment variables before running:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `./state/` | Where state files live |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Pairing token validity (future) |

For LAN access from your phone:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

## First Boot

### 1. Bootstrap the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Stopping any existing daemon...
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
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
curl http://127.0.0.1:8080/status
```

Expected:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:00:00+00:00"
}
```

## Pairing Your Phone

### 1. Start the Daemon in LAN Mode

On your server:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
./scripts/bootstrap_home_miner.sh
```

### 2. Find Your Server's LAN IP

```bash
ip addr show | grep "inet "
# Look for 192.168.x.x or 10.0.x.x
```

### 3. Pair via CLI

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:05:00+00:00"
}
paired my-phone
capability=observe,control
```

### 4. Note the Server IP

You'll need `http://<server-ip>:8080` for the command center.

## Opening the Command Center

### Option A: Direct HTML (Same Machine)

```bash
open apps/zend-home-gateway/index.html
# Or navigate in browser to:
# file:///opt/zend/apps/zend-home-gateway/index.html
```

### Option B: LAN Access (Phone on Same Network)

1. Serve the HTML file:

```bash
cd /opt/zend
python3 -m http.server 3000 --bind 0.0.0.0 --directory apps/zend-home-gateway
```

2. On your phone, open:
   ```
   http://<server-ip>:3000/index.html
   ```

### Option C: Configure Daemon for LAN

Modify `services/home-miner-daemon/daemon.py` to serve the HTML:

```python
# Add import
import mimetypes

# In GatewayHandler, add:
def do_GET(self):
    if self.path == '/' or self.path == '/index.html':
        # Serve index.html
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open('apps/zend-home-gateway/index.html', 'rb') as f:
            self.wfile.write(f.read())
        return
```

Then access `http://<server-ip>:8080/` from your phone.

## Daily Operations

### Check Status

```bash
./scripts/read_miner_status.sh --client my-phone
```

Output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T11:00:00+00:00"
}
status=stopped
mode=paused
freshness=2026-03-22T11:00:00+00:00
```

### Start Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action start
```

Expected:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
acknowledged=true
note='Action accepted by home miner, not client device'
```

### Set Mining Mode

```bash
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

Modes: `paused`, `balanced`, `performance`

### Stop Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action stop
```

### View Events (Inbox)

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

## Recovery

### Daemon Won't Start (Port in Use)

```bash
# Find what's using the port
lsof -i :8080

# Kill it
kill <PID>

# Or restart
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### State Corruption

```bash
# Clear state and re-bootstrap
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Connect

1. Verify server IP: `ip addr show | grep inet`
2. Check firewall: `sudo ufw allow 8080`
3. Test from server: `curl http://127.0.0.1:8080/health`
4. Test from same machine: `curl http://<server-ip>:8080/health`

### Pairing Lost

```bash
# Re-pair (may need to clear state first)
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Security Notes

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. This means:
- Only processes on the same machine can connect
- Your phone on the LAN cannot connect without changing `ZEND_BIND_HOST`

### Opening to LAN

Setting `ZEND_BIND_HOST=0.0.0.0` makes the daemon accessible from your LAN. This is fine for home use but:

- Do NOT expose port 8080 to the internet
- Do NOT trust untrusted networks
- Consider a VPN for remote access instead

### No Authentication (Milestone 1)

Milestone 1 has no password or token authentication. Access control is:
- Network-level (who can reach the daemon)
- Device-level (which devices are paired)

### Pairing Capabilities

When pairing, grant only the capabilities needed:
- `observe` — View status only
- `control` — Start/stop/mode changes (also includes observe)

## Systemd Service (Optional)

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=127.0.0.1"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/opt/zend/scripts/bootstrap_home_miner.sh --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend-home
sudo systemctl start zend-home
sudo systemctl status zend-home
```

## Logs

The daemon prints to stdout. With systemd:

```bash
journalctl -u zend-home -f
```

Direct output:

```bash
./scripts/bootstrap_home_miner.sh --daemon
# Output appears in terminal
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Daemon state | `state/principal.json` | Principal identity |
| Pairing records | `state/pairing-store.json` | Device permissions |
| Event journal | `state/event-spine.jsonl` | Operations log |
| PID file | `state/daemon.pid` | Running daemon PID |
