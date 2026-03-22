# Operator Quickstart

This guide walks you through deploying Zend on home hardware—a Raspberry Pi, old laptop, or any Linux box. No cloud services, no internet-exposed APIs.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86_64 or ARM | ARMv8+ (Raspberry Pi 3+) |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB free | 8 GB+ SDD/HDD |
| OS | Linux (any distro) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet or WiFi | Ethernet for stability |
| Python | 3.10+ | 3.10+ |

Zend runs entirely offline after setup. No internet connection required for local operation.

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or later
```

If not, install Python 3.10+:

```bash
# Raspberry Pi OS / Debian / Ubuntu
sudo apt update
sudo apt install python3 python3-venv
```

### 3. Create State Directory

```bash
sudo mkdir -p /opt/zend/state
sudo chown -R $USER:$USER /opt/zend
```

## Configuration

### Environment Variables

Create a configuration file at `/opt/zend/.env` (optional):

```bash
# /opt/zend/.env
ZEND_BIND_HOST=0.0.0.0          # Bind to all interfaces (for LAN access)
ZEND_BIND_PORT=8080             # HTTP port
ZEND_STATE_DIR=/opt/zend/state  # Where state files live
ZEND_DAEMON_URL=http://localhost:8080  # CLI target
```

### Binding Decisions

| `ZEND_BIND_HOST` | Use Case |
|------------------|----------|
| `127.0.0.1` | Local only (default). Phone must be on same device. |
| `0.0.0.0` | LAN access. Phone connects over local network. |
| `192.168.x.x` | Specific interface. Use when you know your LAN IP. |

**Security Note:** Binding to `0.0.0.0` exposes the daemon on your LAN. Only do this if your network is trusted. The daemon has no authentication in phase one.

## First Boot

### Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1234)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "abc123",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

### Verify Health

```bash
curl http://localhost:8080/health
```

Expected:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### Run at Startup (Optional)

Create a systemd service at `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/opt/zend/scripts/bootstrap_home_miner.sh --daemon
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
```

Check status:

```bash
sudo systemctl status zend
```

## Pairing a Phone

### Find Your Server's LAN IP

On the server:

```bash
hostname -I | awk '{print $1}'
# Example output: 192.168.1.100
```

### Open the Command Center

On your phone:
1. Connect to the same WiFi network
2. Open a browser
3. Navigate to `http://<server-ip>:8080`
4. Or open the file `/opt/zend/apps/zend-home-gateway/index.html` directly if served

### Verify Connection

The command center should show:
- **Miner Status**: Stopped
- **Mode**: Paused

If you see "Unable to connect to Zend Home":
1. Check the server IP is correct
2. Verify the daemon is running: `curl http://localhost:8080/health`
3. Check your phone is on the same network
4. Temporarily disable mobile data to force LAN connection

### Pair the Phone

From the server:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Or via CLI for observe-only:

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe
```

## Daily Operations

### Check Miner Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status --client my-phone

# Via HTTP
curl http://localhost:8080/status
```

### Start/Stop Mining

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

### Change Mining Mode

```bash
# Pause all mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode paused

# Balanced (50 kH/s simulated)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Performance (150 kH/s simulated)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode performance
```

### View Event Log

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt

# Last 20 events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Recovery

### State Is Corrupted

If the daemon won't start or you see JSON errors:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup current state (optional)
mv state state.backup

# Restart (creates fresh state)
./scripts/bootstrap_home_miner.sh

# If you need the old state:
# mv state.backup state
```

### Daemon Won't Start

1. Check if another process is using the port:
   ```bash
   lsof -i :8080
   # or
   sudo netstat -tlnp | grep 8080
   ```

2. Kill the old process or change `ZEND_BIND_PORT`

3. Check state directory permissions:
   ```bash
   ls -la state/
   # Should be owned by the user running the daemon
   ```

### Phone Can't Connect

1. Verify server IP:
   ```bash
   hostname -I
   ```

2. Ping the server from your phone:
   ```bash
   # From phone terminal
   ping 192.168.1.100
   ```

3. Check firewall (on server):
   ```bash
   sudo iptables -L -n | grep 8080
   # If blocked, allow:
   sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
   ```

### Lost Pairing Record

To pair a device that was previously paired:

```bash
# List current pairings
cat state/pairing-store.json

# Pair again (if device name exists, it will fail)
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

If the device was already paired, delete its record first:

```bash
# Edit pairing-store.json and remove the entry
nano state/pairing-store.json
```

## Security Checklist

- [ ] Daemon binds to trusted network only
- [ ] No sensitive data in state directory (it's local only)
- [ ] Firewall blocks port 8080 from internet
- [ ] No internet-facing services on same box without isolation
- [ ] Regular backups of state directory

### Network Isolation

To isolate Zend from other LAN devices:

```bash
# Allow only specific phone IPs
sudo iptables -A INPUT -p tcp --dport 8080 -s 192.168.1.50 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -s 192.168.1.51 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
```

## Upgrading

```bash
cd /opt/zend
git pull

# Restart daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

State files are preserved across upgrades.

## Backup

To backup your Zend configuration:

```bash
# Backup state
tar -czf zend-backup-$(date +%Y%m%d).tar.gz state/

# List contents
tar -tzf zend-backup-20260322.tar.gz
```

Restore:
```bash
tar -xzf zend-backup-20260322.tar.gz
```

## Uninstall

```bash
# Stop and disable service (if using systemd)
sudo systemctl stop zend
sudo systemctl disable zend

# Remove service file
sudo rm /etc/systemd/system/zend.service

# Remove application
sudo rm -rf /opt/zend

# Optional: remove state
# rm -rf /opt/zend/state
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Unable to connect" in browser | Wrong IP or network | Verify `hostname -I` and phone on same network |
| `curl: Failed to connect` | Daemon not running | `./scripts/bootstrap_home_miner.sh` |
| JSON parse error | Corrupted state file | Backup and reset state |
| Port already in use | Another process on 8080 | `ZEND_BIND_PORT=8081` or kill old process |
| Permission denied | Wrong file owner | `sudo chown -R $USER:$USER /opt/zend` |
| Phone can't reach daemon | Firewall blocking | `sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT` |
