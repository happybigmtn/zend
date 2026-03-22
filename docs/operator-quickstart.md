# Operator Quickstart

This guide helps you deploy Zend on home hardware. You'll run the mining daemon on a Linux machine in your home, then control it from your phone.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86-64 or ARM | ARM64 (Raspberry Pi 4+) |
| RAM | 256 MB | 512 MB+ |
| Storage | 100 MB | 1 GB+ |
| OS | Linux (any distro) | Raspberry Pi OS, Ubuntu |
| Network | Ethernet or WiFi | Ethernet |
| Python | 3.10+ | 3.10+ |

### Tested Hardware

- Raspberry Pi 4 (4GB)
- Raspberry Pi 3B+
- Generic x86-64 Linux box
- macOS (for development)

## Installation

### 1. Clone the Repository

SSH into your home machine and clone the repository:

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or higher
```

### 3. No Dependencies Required

Zend uses Python standard library only. No pip install, no virtual environment needed.

## Configuration

### Environment Variables

Create a configuration file or set variables before starting:

```bash
# /opt/zend/.env (optional)
export ZEND_BIND_HOST=0.0.0.0        # Listen on all interfaces for LAN access
export ZEND_BIND_PORT=8080           # Daemon port
export ZEND_STATE_DIR=/opt/zend/state # State storage location
```

### Network Considerations

| Binding | Use Case | Security |
|---------|----------|----------|
| `127.0.0.1` | Dev only | Localhost only |
| `0.0.0.0` | Home LAN | LAN only, no internet exposure |
| LAN IP (e.g., `192.168.1.100`) | Specific interface | Same as above |

**Important**: Never expose the daemon to the public internet.

## First Boot

### 1. Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Stopping daemon (if running)
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "..."
}
[INFO] Bootstrap complete
```

### 2. Verify Daemon is Running

From the same machine:
```bash
curl http://localhost:8080/health
# Output: {"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### 3. Find Your Machine's LAN IP

```bash
hostname -I | awk '{print $1}'
# Example output: 192.168.1.100
```

## Pairing a Phone

### 1. Get Your Machine's IP Address

Note the IP from the previous step. You'll need it for the next step.

### 2. Prepare the Command Center

The command center is a single HTML file. Options:

**Option A: Open directly (file://)**
Copy `apps/zend-home-gateway/index.html` to your phone, or sync via cloud storage.

**Option B: Serve locally**
On the home machine:
```bash
cd /opt/zend/apps/zend-home-gateway
python3 -m http.server 8081
```
Then access from phone: `http://192.168.1.100:8081/index.html`

### 3. Configure the Gateway

Before opening the command center, you need to point it to your daemon.

In the `index.html` file, find this line:
```javascript
const API_BASE = 'http://127.0.0.1:8080';
```

Change it to your home machine's IP:
```javascript
const API_BASE = 'http://192.168.1.100:8080';
```

### 4. Test the Connection

Open the command center in your phone's browser. You should see:
- Status hero showing "Stopped"
- Mode switcher (Paused/Balanced/Performance)
- Start/Stop buttons

If you see an alert about being unable to connect:
- Verify the daemon is running on the home machine
- Verify your phone is on the same network
- Check firewall settings (see Troubleshooting below)

## Daily Operations

### Check Miner Status

On your home machine:
```bash
python3 services/home-miner-daemon/cli.py status
```

### Control Mining from CLI

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Change mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### View Event Receipts

```bash
# Recent events
python3 services/home-miner-daemon/cli.py events --limit 10

# Filter by type
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### Stop and Start the Daemon

```bash
# Stop
/opt/zend/scripts/bootstrap_home_miner.sh --stop

# Start
/opt/zend/scripts/bootstrap_home_miner.sh

# Check status
/opt/zend/scripts/bootstrap_home_miner.sh --status
```

## Recovery

### Daemon Won't Start

1. Check if a process is already using port 8080:
   ```bash
   lsof -i :8080
   # Kill any existing process
   ```

2. Verify state directory is writable:
   ```bash
   ls -la /opt/zend/state/
   ```

3. Check for corrupted state files:
   ```bash
   # Backup and reset state
   mv state state.backup
   ./scripts/bootstrap_home_miner.sh
   ```

### State is Corrupted

If you see JSON parse errors or strange behavior:

```bash
# 1. Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# 2. Backup state
cp -r state state.backup

# 3. Remove corrupted files
rm -f state/principal.json state/pairing-store.json state/event-spine.jsonl

# 4. Fresh bootstrap
./scripts/bootstrap_home_miner.sh

# 5. Re-pair devices
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control
```

### Phone Can't Connect

1. Verify network connectivity:
   ```bash
   # From phone, test:
   curl http://192.168.1.100:8080/health
   ```

2. Check firewall on home machine:
   ```bash
   # Allow port 8080 for LAN
   sudo ufw allow from 192.168.0.0/16 to any port 8080
   ```

3. Verify daemon is listening:
   ```bash
   sudo netstat -tlnp | grep 8080
   # Should show python3 listening on 0.0.0.0:8080
   ```

## Security Checklist

- [ ] Daemon bound to LAN IP, not 0.0.0.0 (unless you understand the risk)
- [ ] No port forwarding configured on router
- [ ] Firewall blocks external access to port 8080
- [ ] State directory has restricted permissions:
  ```bash
  chmod 700 /opt/zend/state
  chmod 600 /opt/zend/state/*.json
  ```
- [ ] Regular backups of state directory

## Backup and Restore

### Backup

```bash
# Create backup
tar -czf zend-backup-$(date +%Y%m%d).tar.gz \
  -C /opt/zend state/

# Store off-site or on external drive
```

### Restore

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Restore state
tar -xzf zend-backup-20260322.tar.gz -C /opt/zend

# Verify
python3 services/home-miner-daemon/cli.py status

# Start daemon
./scripts/bootstrap_home_miner.sh
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Unable to connect" alert | Phone can't reach daemon | Check network, firewall, IP address |
| Health check fails | Daemon not running | Restart with bootstrap script |
| Mode changes don't persist | State not saved | Check state directory permissions |
| 502/504 errors | Wrong port or daemon restarted | Verify port, restart daemon |
| Slow response | Network congestion | Use wired Ethernet instead of WiFi |

## Logs

The daemon doesn't write log files by default. To capture logs:

```bash
# Redirect output to file
./scripts/bootstrap_home_miner.sh > /var/log/zend.log 2>&1 &

# Or use systemd for auto-restart (see below)
```

## Running as a Service (Optional)

For auto-start on boot with systemd:

```ini
# /etc/systemd/system/zend.service
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Install service
sudo cp zend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend

# Check status
sudo systemctl status zend
```
