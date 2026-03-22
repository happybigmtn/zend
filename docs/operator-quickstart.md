# Operator Quickstart

This guide helps you deploy Zend on home hardware. By the end, you will have:
- The daemon running on your Linux machine
- A phone paired and able to view status and control mining
- Access to the command center from the phone's browser

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86_64 or ARM | ARMv8+ (Raspberry Pi 4+) |
| RAM | 256 MB | 512 MB+ |
| Storage | 100 MB | 1 GB |
| OS | Linux (any distro) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet or WiFi | Ethernet |

Zend has been tested on:
- Raspberry Pi 4 (ARM64)
- Ubuntu 22.04 (x86_64)
- macOS (for development)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

Or if you already have it locally:

```bash
cd ~/zend
```

### Step 2: Verify Python

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

If not installed, install Python 3.10+:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install python3 python3-venv
```

### Step 3: Bootstrap the Daemon

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
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

The daemon is now running in the background.

## Configuration

### Environment Variables

Create a systemd service file at `/etc/systemd/system/zend.service`:

```ini
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
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend
sudo systemctl start zend
sudo systemctl status zend
```

### Network Configuration

By default, the daemon binds to `127.0.0.1` (localhost only). To access from other devices on your LAN:

```bash
# Set bind address to all interfaces
export ZEND_BIND_HOST=0.0.0.0

# Or to bind to LAN interface only (recommended)
export ZEND_BIND_HOST=192.168.1.100  # Your machine's LAN IP
```

For systemd, edit the service file's `Environment` line:

```ini
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
```

### State Directory

By default, state is stored in `./state` relative to the repository root. To change:

```bash
export ZEND_STATE_DIR=/var/lib/zend/state
```

For systemd:

```ini
Environment="ZEND_STATE_DIR=/var/lib/zend/state"
```

Ensure the directory exists and is writable:

```bash
sudo mkdir -p /var/lib/zend/state
sudo chown -R zend:zend /var/lib/zend
```

## Pairing a Phone

### From the Command Line

On the server:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00Z"
}
```

### Capabilities Reference

| Capability | What it allows |
|------------|----------------|
| `observe` | View miner status and health |
| `control` | Start/stop mining, change modes |

Grant only `observe` for read-only access.

## Opening the Command Center

### On the Phone

1. Open your browser (Chrome, Safari, Firefox)
2. Navigate to `http://<server-ip>:8080/apps/zend-home-gateway/index.html`

   Example: `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`

3. The command center should load and show miner status

### Troubleshooting Browser Access

**Connection refused:**
- Verify daemon is running: `curl http://localhost:8080/health`
- Check firewall: `sudo ufw allow 8080`

**Connection timeout:**
- Verify IP address is correct
- Check both devices are on the same network

**Command center shows "Unable to connect":**
- The daemon may be bound to `127.0.0.1` only
- Change `ZEND_BIND_HOST` to `0.0.0.0` or your LAN IP

## Daily Operations

### Check Miner Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status --client my-phone

# Via curl
curl http://localhost:8080/status
```

Example output:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00Z"
}
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
# Pause (stop mining but keep daemon running)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode paused

# Balanced (normal operation)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Performance (maximum power)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode performance
```

### View Event Log

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 10
```

### Check Daemon Health

```bash
curl http://localhost:8080/health
```

## Recovery

### State Corruption

If the daemon fails to start or state seems corrupted:

1. Stop the daemon:
   ```bash
   ./scripts/bootstrap_home_miner.sh --stop
   ```

2. Backup and reset state:
   ```bash
   mv state state.backup
   ./scripts/bootstrap_home_miner.sh
   ```

   Warning: This creates a new PrincipalId and invalidates existing pairings.

### Daemon Won't Start

1. Check port availability:
   ```bash
   lsof -i :8080
   ```

2. Kill any process using the port:
   ```bash
   kill <PID>
   ```

3. Check Python version:
   ```bash
   python3 --version
   ```

4. Run daemon directly to see errors:
   ```bash
   python3 services/home-miner-daemon/daemon.py
   ```

### Pairing Lost

If a device loses pairing:

1. Remove old pairing:
   ```bash
   rm state/pairing-store.json
   ```

2. Re-pair:
   ```bash
   ./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
   ```

## Security

### LAN-Only by Default

The daemon is designed for LAN-only access. Do not expose port 8080 to the internet.

### Firewall Configuration

```bash
# Allow localhost (always)
sudo ufw allow from 127.0.0.1 to any port 8080

# Allow LAN (adjust subnet as needed)
sudo ufw allow from 192.168.0.0/16 to any port 8080

# Deny all other access
sudo ufw deny 8080
```

### No Internet-Facing Control

Phase one does not support remote access. If you need remote access:
- Use a VPN (WireGuard, Tailscale)
- Do not port-forward directly
- Consider Tailscale's exit nodes

### Principal Identity

The `principal.json` file contains your identity. Back it up:
```bash
cp state/principal.json ~/backup-principal.json
```

## Systemd Service Management

### View Logs

```bash
sudo journalctl -u zend -f
```

### Restart Daemon

```bash
sudo systemctl restart zend
```

### Stop Daemon

```bash
sudo systemctl stop zend
```

### Disable Auto-Start

```bash
sudo systemctl disable zend
```

## Quick Reference

| Task | Command |
|------|---------|
| Start daemon | `./scripts/bootstrap_home_miner.sh` |
| Stop daemon | `./scripts/bootstrap_home_miner.sh --stop` |
| Check status | `curl http://localhost:8080/status` |
| Check health | `curl http://localhost:8080/health` |
| Pair phone | `./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control` |
| Start mining | `python3 services/home-miner-daemon/cli.py control --client my-phone --action start` |
| Stop mining | `python3 services/home-miner-daemon/cli.py control --client my-phone --action stop` |
| Change mode | `python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced` |
| View events | `python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20` |
| Open command center | `http://<server-ip>:8080/apps/zend-home-gateway/index.html` |
