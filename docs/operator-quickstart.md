# Operator Quickstart

Deploy Zend on home hardware. This guide covers Raspberry Pi, mini PCs, or any Linux box on your home network.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB | 4 GB |
| OS | Linux (any) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet | Ethernet |

Python 3.10+ is required. Most modern systems have this.

## Installation

### 1. Clone the Repository

SSH into your hardware and run:

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Must show Python 3.10 or higher
```

### 3. Create State Directory

```bash
sudo mkdir -p /opt/zend/state
sudo chown $USER:$USER /opt/zend/state
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | State file location |
| `ZEND_BIND_HOST` | `127.0.0.1` | Network interface (change for LAN) |
| `ZEND_BIND_PORT` | `8080` | TCP port |

### LAN Configuration

To access from other devices on your network:

```bash
export ZEND_BIND_HOST=0.0.0.0          # Or your LAN IP (e.g., 192.168.1.100)
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=/opt/zend/state
```

**Security Note:** Binding to `0.0.0.0` exposes the daemon on your local network. Only do this on trusted LANs. Phase 1 does not include authentication; rely on network-level access control.

## First Boot

### 1. Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

**Expected output:**
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
python3 services/home-miner-daemon/cli.py health
```

**Expected output:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

### 3. Check Initial Status

```bash
python3 services/home-miner-daemon/cli.py status
```

**Expected output:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

## Pairing a Phone

### 1. Find Your Hardware's LAN IP

On the hardware:
```bash
hostname -I | awk '{print $1}'
# Example: 192.168.1.100
```

### 2. Open the Command Center

On your phone:

1. Open the browser
2. Navigate to `http://<hardware-ip>:8080/apps/zend-home-gateway/index.html`

**Note:** For milestone 1, the HTML file must be served from the daemon or a separate HTTP server. Simplest approach:

```bash
# On the hardware, serve the HTML file:
cd /opt/zend
python3 -m http.server 8080 --directory apps/zend-home-gateway
# Access at http://<hardware-ip>:8080/index.html
```

### 3. Pair the Device

From your phone's browser console (or via CLI):

```bash
# SSH into hardware
ssh user@<hardware-ip>

# Pair with control capabilities
python3 /opt/zend/services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

**Expected output:**
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop
```

### Change Mode

```bash
# Balanced mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode performance
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events \
  --client my-phone \
  --kind control_receipt
```

## Daemon Management

### Run as Background Service

Create `/etc/systemd/system/zend-daemon.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment=ZEND_BIND_HOST=0.0.0.0
Environment=ZEND_BIND_PORT=8080
Environment=ZEND_STATE_DIR=/opt/zend/state
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend-daemon
sudo systemctl start zend-daemon
```

Check status:

```bash
sudo systemctl status zend-daemon
```

### View Logs

```bash
# Systemd journal
sudo journalctl -u zend-daemon -f

# Or check the daemon PID
cat /opt/zend/state/daemon.pid
```

## Recovery

### State Corruption

If the daemon fails to start or state is corrupted:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Reset state (WARNING: loses all pairing info)
rm -rf /opt/zend/state/*

# Restart
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

```bash
# Check port availability
lsof -i :8080

# Check Python version
python3 --version

# Check state directory permissions
ls -la /opt/zend/state/
```

### CLI Can't Connect

```bash
# Verify daemon is running
python3 services/home-miner-daemon/cli.py health

# Check binding address
# Make sure ZEND_BIND_HOST matches (127.0.0.1 for local, 0.0.0.0 for LAN)
```

## Security

### Network Access

- **Phase 1 is LAN-only.** Do not expose the daemon to the internet.
- Bind to `127.0.0.1` for local-only access
- Bind to LAN IP (e.g., `192.168.1.100`) for local network access
- Never bind to `0.0.0.0` on untrusted networks

### Firewall Rules

```bash
# Allow local network access (example with ufw)
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Block external access
sudo ufw deny 8080
```

### Pairing Tokens

- Pairing tokens expire after initial use
- Each device needs explicit pairing
- Revoke unused pairings to maintain security

### What to Check

- [ ] Daemon binds to expected interface only
- [ ] Firewall blocks external access
- [ ] Pairing records are reviewed
- [ ] State directory is not world-readable

### What NOT to Expose

- Do not port-forward to the daemon
- Do not use in DMZ configurations
- Do not trust untrusted networks

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop zend-daemon
sudo systemctl disable zend-daemon

# Remove service file
sudo rm /etc/systemd/system/zend-daemon.service
sudo systemctl daemon-reload

# Remove application
sudo rm -rf /opt/zend
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Address already in use" | Another process using port 8080. Run `lsof -i :8080` to find it. |
| "Daemon unavailable" | Daemon not running. Run `bootstrap_home_miner.sh` |
| "Unauthorized" | Device lacks capability. Re-pair with correct capabilities. |
| UI not loading | Serve HTML from daemon or separate server. |
| Pairing failed | State may be corrupted. Reset with `rm -rf state/*` |

## Support

- Check `docs/architecture.md` for system understanding
- Review `references/` for contracts
- See `plans/` for implementation details
