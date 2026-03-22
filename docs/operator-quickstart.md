# Operator Quickstart

Deploy Zend on your home hardware. This guide covers everything from initial
setup to daily operations. No developer experience required.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Boot](#first-boot)
5. [Pairing a Phone](#pairing-a-phone)
6. [Opening the Command Center](#opening-the-command-center)
7. [Daily Operations](#daily-operations)
8. [Recovery](#recovery)
9. [Security](#security)

---

## Hardware Requirements

### Minimum

- Linux machine (Raspberry Pi 4+ works great)
- ARMv8 or x86_64 processor
- 1GB RAM
- 1GB available storage
- Python 3.10 or later
- Network access (wired or WiFi)

### Recommended

- Raspberry Pi 4 (4GB RAM) or any modern mini PC
- Wired Ethernet for stability
- 16GB+ SD card or SSD
- Uninterrupted power supply (optional)

### Not Supported

- Windows desktop (use WSL or Docker)
- macOS (should work, not officially tested)
- Android/iOS as daemon host (not supported)

---

## Installation

### 1. Install Python

Most Linux distributions have Python 3.10+ pre-installed. Verify:

```bash
python3 --version
```

If not installed:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install python3

# Fedora
sudo dnf install python3
```

### 2. Clone the Repository

```bash
# Install git if needed
sudo apt install git

# Clone the repo
git clone <repo-url> zend
cd zend
```

### 3. Verify Installation

```bash
python3 --version  # Should be 3.10+
ls scripts/        # Should show bootstrap_home_miner.sh
```

**No pip install needed** — Zend uses Python stdlib only.

---

## Configuration

### Environment Variables

Create a configuration file or set variables before starting:

```bash
# Optional: Create a config file
cat > ~/.zendrc << 'EOF'
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=~/zend/state
EOF

# Source it for each session
source ~/.zendrc
```

### Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Port for the daemon |
| `ZEND_STATE_DIR` | `./state` | Directory for state files |

### Network Setup

For LAN access from your phone:

```bash
# Bind to all interfaces (for LAN access)
export ZEND_BIND_HOST=0.0.0.0

# Find your machine's IP
ip addr show | grep "inet "
# Example output: inet 192.168.1.100/24

# Or use hostname
hostname -I
```

**Important:** `ZEND_BIND_HOST=0.0.0.0` makes the daemon accessible from any
device on your LAN. This is intended for home use. See [Security](#security).

---

## First Boot

### Run the Bootstrap Script

```bash
cd zend
./scripts/bootstrap_home_miner.sh
```

**Expected Output:**

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

### Verify the Daemon is Running

```bash
# Check health
curl http://127.0.0.1:8080/health

# Expected:
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Check status
curl http://127.0.0.1:8080/status

# Expected:
# {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Start on Boot (Optional)

Create a systemd service:

```bash
sudo cat > /etc/systemd/system/zend.service << 'EOF'
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/home/pi/zend/scripts/bootstrap_home_miner.sh --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend
```

---

## Pairing a Phone

### 1. Find Your Daemon's LAN Address

On your Zend machine:

```bash
hostname -I
```

Note the IP address (e.g., `192.168.1.100`).

### 2. Configure Phone Network (Temporarily)

For initial setup, we need to access the daemon from your phone. In a browser
on your phone:

```
http://192.168.1.100:8080/health
```

Should return JSON. If not, check firewall rules.

### 3. Create a Pairing

On your Zend machine:

```bash
# Pair a new device
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

**Expected Output:**

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T..."
}
```

### 4. Verify Pairing

```bash
# List all paired devices
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
```

---

## Opening the Command Center

### Option 1: Direct File Access

1. On your phone, open the file browser
2. Navigate to the Zend repo folder
3. Open `apps/zend-home-gateway/index.html`
4. Allow file access if prompted

### Option 2: Local Web Server

```bash
# Start a simple server
cd apps/zend-home-gateway
python3 -m http.server 8081

# Access from phone:
# http://192.168.1.100:8081/
```

### Option 3: Copy to Phone Storage

1. Copy `index.html` to your phone
2. Open in any browser

### Expected Interface

The command center should show:

- **Header:** "Zend" with device name badge
- **Status Hero:** Miner state (Stopped/Running) with indicator
- **Mode Switcher:** Paused / Balanced / Performance buttons
- **Quick Actions:** Start Mining / Stop Mining buttons
- **Latest Receipt:** Most recent operation
- **Bottom Nav:** Home / Inbox / Agent / Device tabs

---

## Daily Operations

### Check Miner Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status

# Via curl
curl http://127.0.0.1:8080/status | python3 -m json.tool
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode performance
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

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Recent events
python3 services/home-miner-daemon/cli.py events --limit 5

# Specific type
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### View Daemon Logs

```bash
# If running in foreground
# (Ctrl+C to stop)

# If running in background
tail -f ~/zend/state/event-spine.jsonl
```

---

## Recovery

### State Corruption

If the daemon fails to start or state seems corrupted:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup state
mv state state.backup

# Create fresh state
./scripts/bootstrap_home_miner.sh

# Re-pair devices
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
```

### Daemon Won't Start

```bash
# Check if already running
cat state/daemon.pid
ps aux | grep daemon.py

# Kill any stale process
pkill -f daemon.py

# Restart
./scripts/bootstrap_home_miner.sh
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8080

# Change to different port
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Reset Everything

```bash
# Full reset
./scripts/bootstrap_home_miner.sh --stop
rm -rf state
./scripts/bootstrap_home_miner.sh
```

---

## Security

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. Only processes on the same machine
can access it.

### LAN Access Considerations

Setting `ZEND_BIND_HOST=0.0.0.0` exposes the daemon to your entire LAN:

**Safe because:**
- Home networks are typically firewalled from the internet
- No authentication bypasses exist (pairing required for control)
- No sensitive data stored in plain text

**Caution:**
- Don't expose port 8080 to the internet
- Untrusted LAN devices could access status (observe capability)
- Control requires paired device

### Firewall Setup

```bash
# Allow LAN access, block internet
sudo ufw allow from 192.168.0.0/16 to any port 8080
sudo ufw deny to any port 8080
```

### Best Practices

1. **Use wired Ethernet** when possible for stability
2. **Keep firmware updated** on your hardware
3. **Don't expose port 8080** to the internet
4. **Pair only devices you control**
5. **Revoke unused pairings** regularly

### What Not to Do

- ❌ Expose port 8080 directly to the internet
- ❌ Use `ZEND_BIND_HOST=0.0.0.0` in a shared office network
- ❌ Leave the default port unchanged on a public network
- ❌ Pair with untrusted devices

---

## Troubleshooting

### Phone Can't Reach Daemon

1. Check daemon is running:
   ```bash
   curl http://127.0.0.1:8080/health
   ```

2. Check firewall:
   ```bash
   sudo ufw status
   ```

3. Verify IP address:
   ```bash
   hostname -I
   ```

4. Try pinging from phone (if supported)

### Command Center Shows "Unable to Connect"

1. Verify daemon running
2. Check `ZEND_BIND_HOST` is set correctly
3. Try direct IP: `http://192.168.1.100:8080/health`
4. Check phone and daemon are on same network

### Controls Not Working

1. Verify device is paired:
   ```bash
   python3 services/home-miner-daemon/cli.py events --kind pairing_granted
   ```

2. Check device has control capability
3. Try re-pairing with control capability

### Need Help?

- Check [docs/api-reference.md](api-reference.md) for API details
- Check [docs/architecture.md](architecture.md) for system design
- Open a GitHub issue with error messages and steps to reproduce
