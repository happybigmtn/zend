# Operator Quickstart

Deploy Zend on your home hardware. This guide covers everything from first
boot to daily operations.

## Hardware Requirements

- **Minimum**: Raspberry Pi 4 (or similar), 1GB RAM, Python 3.10+
- **Recommended**: Any Linux machine, 2GB RAM, Python 3.10+
- **Storage**: 50MB for the repo, 10MB for state
- **Network**: Ethernet or WiFi, same network as your phone

Zend runs on any machine that can run Python. No GPU required.

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

No pip install needed. Zend uses only the Python standard library.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` for LAN access from other devices. |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `state/` | Directory for state files |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

For LAN access (recommended for home deployment):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

### Persistent Configuration

Create `/etc/zend/environment` (or add to `.bashrc`):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

## First Boot

### 1. Bootstrap the System

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
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

The daemon is now running. Note the `principal_id` and `pairing_id`—you'll need
them to pair your phone.

### 2. Verify the Daemon

```bash
curl http://localhost:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Access from Another Machine

From any device on the same LAN:

```
http://<your-pi-ip>:8080/
```

Find your IP:

```bash
hostname -I | awk '{print $1}'
```

## Pairing Your Phone

### Option A: Use the Command Center

1. Open `apps/zend-home-gateway/index.html` in your phone's browser
2. The page should connect to the daemon automatically
3. If it shows "Unable to connect", check the IP address and firewall

### Option B: Command-Line Pairing

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Opening the Command Center

### From the Browser

1. Ensure your phone is on the same LAN as the daemon
2. Open `http://<daemon-ip>:8080/` in your browser
3. Or open the local file `apps/zend-home-gateway/index.html` and edit the
   `API_BASE` constant to point to your daemon's IP

### Accessing the HTML File

Copy the file to your phone:

```bash
# On your phone/computer, serve the file:
cd /opt/zend
python3 -m http.server 8081

# Then open http://<your-ip>:8081/apps/zend-home-gateway/index.html
```

Or use a file transfer tool to copy `apps/zend-home-gateway/index.html` directly.

## Daily Operations

### Check Miner Status

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

### View Recent Events

```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Check Daemon Health

```bash
curl http://localhost:8080/health
```

## Managing Multiple Devices

### List Paired Devices

```bash
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
```

### Add a New Device

```bash
./scripts/pair_gateway_client.sh --client my-tablet --capabilities observe
```

### Revoke a Device

Currently requires manual state editing (see Recovery below).

## Recovery

### State is Corrupted

If the daemon won't start or shows errors:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start (Port in Use)

```bash
# Find and kill the process
lsof -i :8080
kill <PID>

# Or restart
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Connect

1. Verify the daemon is running: `curl http://localhost:8080/health`
2. Check the IP address: `hostname -I`
3. Check firewall: `sudo ufw status` or `sudo iptables -L`
4. Allow the port: `sudo ufw allow 8080/tcp`

### Event Spine is Empty After Reboot

The event spine is in `state/event-spine.jsonl`. If it's missing, events start
fresh. This is expected—each boot is a new session.

## Security

### LAN-Only Binding

By default, the daemon binds to localhost. For LAN access, bind to `0.0.0.0`
but be aware:

- Any device on your LAN can access the daemon
- No authentication is required in milestone 1
- Do not expose port 8080 to the internet

### What to Check

- [ ] Daemon binds only to LAN interface, not public IP
- [ ] Phone is on the same trusted network
- [ ] No port forwarding set up for port 8080
- [ ] State directory is not accessible to other users

### What NOT to Do

- Don't expose the daemon port to the internet
- Don't run as root unless necessary
- Don't store sensitive data in state files without encryption

## Systemd Service (Optional)

Run the daemon as a service so it starts on boot:

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable zend
sudo systemctl start zend
sudo systemctl status zend
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Unable to connect" in browser | Check daemon IP and port, check firewall |
| `curl` hangs | Daemon not running; run bootstrap |
| Permission denied on state | Run as the user who owns the state directory |
| Python import errors | Ensure Python 3.10+; stdlib only, no pip needed |
| Port already in use | Kill existing process: `lsof -i :8080` then `kill <PID>` |
| Status shows stale | Daemon health check failing; check logs |
| Mode change doesn't work | Verify device has `control` capability |

## Logs

The daemon logs to stdout. If running via systemd:

```bash
journalctl -u zend -f
```

If running manually:

```bash
cd services/home-miner-daemon
python3 daemon.py
# Watch output
```

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or if running manually: `Ctrl+C`
