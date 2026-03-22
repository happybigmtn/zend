# Operator Quickstart

This guide walks you through deploying Zend on home hardware — a Raspberry Pi, home server, or any Linux box.

## Hardware Requirements

- Any Linux system with Python 3.10+
- Network access (same network as your phone)
- 100MB disk space for state files
- Optional: Static IP or hostname for reliable phone access

**Recommended**: Raspberry Pi 4 or similar single-board computer running Raspberry Pi OS or Ubuntu Server.

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python Version

```bash
python3 --version
# Should show Python 3.10 or later
```

### 3. Bootstrap the Daemon

```bash
sudo -u pi ./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
[INFO] Bootstrap complete
```

### 4. Verify Daemon is Running

```bash
curl http://localhost:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `state/` | Directory for persistent state |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Pairing token validity period |

### Binding for LAN Access

To access Zend from your phone on the same network:

```bash
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh
```

**Security Note**: Binding to `0.0.0.0` exposes the control surface on your local network. This is acceptable for home use behind a router firewall. Do not expose this port to the internet.

### Custom Port

```bash
export ZEND_BIND_PORT=9000
./scripts/bootstrap_home_miner.sh
```

## First Boot Walkthrough

### 1. Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

### 2. Check Status

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
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:00:00+00:00"
}
```

### 3. Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

Expected output:
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

## Pairing a Phone

### 1. Find Your Daemon's IP

```bash
hostname -I | awk '{print $1}'
```

### 2. Update Daemon for LAN Access

```bash
# Stop existing daemon
./scripts/bootstrap_home_miner.sh --stop

# Restart with LAN binding
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh
```

### 3. Pair from CLI (Recommended for First Setup)

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:05:00+00:00"
}
```

### 4. Open the Command Center

On your phone:
1. Open the browser
2. Navigate to `http://<daemon-ip>:8080/`
3. Or open `apps/zend-home-gateway/index.html` from the repo directly

**Note**: The command center is a single HTML file. For phone access, either:
- Serve it locally: `python3 -m http.server 8080 --directory apps/zend-home-gateway`
- Or open the file directly if your browser supports it

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
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

### View Event Log

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Recovery

### State Corruption

If the daemon won't start or behaves unexpectedly:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

**Warning**: This deletes all pairings and event history.

### Daemon Won't Start (Port in Use)

Check what's using the port:
```bash
lsof -i :8080
```

Kill the existing process:
```bash
kill <PID>
```

Or use a different port:
```bash
export ZEND_BIND_PORT=9000
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Connect

1. Verify daemon is running: `curl http://<daemon-ip>:8080/health`
2. Check firewall: `sudo ufw allow 8080/tcp`
3. Verify phone is on same network
4. Try accessing from browser directly

### Miner Not Responding

```bash
# Check daemon health
curl http://localhost:8080/health

# Restart daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

## Security

### LAN-Only Design

Zend is designed for LAN-only access in phase 1. The daemon should only be accessible from your local network.

**Do not**:
- Port forward 8080 to the internet
- Bind to a public IP
- Use in untrusted networks

**Do**:
- Keep your network behind a router firewall
- Use a strong WiFi password
- Consider a VLAN for IoT/smart home devices

### Capability Scoping

Only grant `control` capability to devices you trust:
```bash
# Observe-only device
python3 services/home-miner-daemon/cli.py pair --device guest-phone --capabilities observe

# Full control device
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

## Systemd Service (Optional)

For automatic startup on boot:

```bash
sudo tee /etc/systemd/system/zend.service << 'EOF'
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend/state"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable zend
sudo systemctl start zend
```

Check status:
```bash
sudo systemctl status zend
```

View logs:
```bash
sudo journalctl -u zend -f
```

## Troubleshooting Reference

| Problem | Cause | Solution |
|---------|-------|----------|
| `curl: (7) Failed to connect` | Daemon not running | `./scripts/bootstrap_home_miner.sh` |
| `{"error": "daemon_unavailable"}` | Wrong host/port | Check `ZEND_BIND_HOST` and `ZEND_BIND_PORT` |
| Phone can't access | Firewall blocking | `sudo ufw allow 8080/tcp` |
| `{"error": "unauthorized"}` | Device lacks capability | Re-pair with correct capabilities |
| `{"error": "invalid_mode"}` | Invalid mode value | Use `paused`, `balanced`, or `performance` |
| State corruption | Disk or file errors | Clear `state/` and re-bootstrap |

## Next Steps

- [API Reference](api-reference.md) — All daemon endpoints documented
- [Architecture](architecture.md) — System design details
- [Contributor Guide](contributor-guide.md) — For development work
