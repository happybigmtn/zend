# Operator Quickstart

This guide walks you through deploying Zend on home hardware. By the end, you'll have a running home miner daemon that you can control from your phone's browser.

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

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86_64 or ARM | ARMv8+ (Raspberry Pi 3+) |
| RAM | 256 MB | 512 MB+ |
| Storage | 100 MB | 1 GB+ |
| OS | Linux (any distribution) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet or WiFi | Ethernet (stable) |

**Tested Platforms:**
- Raspberry Pi 3, 4, 5
- Ubuntu Server 22.04+
- Debian 11+
- macOS (development only)

## Installation

### 1. Install Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv

# Verify Python version
python3 --version
# Must be 3.10 or later
```

### 2. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

Or if you don't have git:

```bash
# Download and extract release
curl -L <release-url> -o zend.tar.gz
tar -xzf zend.tar.gz
cd zend
```

### 3. Verify Installation

```bash
python3 -c "import http.server; import json; import socketserver; print('Python OK')"
# Expected: Python OK
```

## Configuration

Zend uses environment variables for configuration.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

### Setting Up for LAN Access

To access Zend from other devices on your network:

```bash
# Set bind address to all interfaces (for LAN access)
export ZEND_BIND_HOST=0.0.0.0

# Or set to your specific LAN IP
export ZEND_BIND_HOST=192.168.1.100
```

### Creating a Systemd Service (Optional)

For automatic startup on Linux:

```bash
# Create service file
sudo nano /etc/systemd/system/zend.service
```

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend

# Check status
sudo systemctl status zend
```

## First Boot

### Starting the Daemon

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
  "pairing_id": "abc123...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:00:00Z"
}
[INFO] Bootstrap complete
```

### Verifying the Daemon

```bash
# Check health
curl http://localhost:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Check status
curl http://localhost:8080/status
# Expected: {"status": "stopped", "mode": "paused", ...}
```

### Starting Mining

```bash
# Start mining in balanced mode
curl -X POST http://localhost:8080/miner/start
# Expected: {"success": true, "status": "running"}

# Check status again
curl http://localhost:8080/status
# Expected: {"status": "running", "mode": "paused", "hashrate_hs": 0}
```

### Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Pairing a Phone

### Step 1: Ensure Daemon is Running

```bash
./scripts/bootstrap_home_miner.sh
```

### Step 2: Find Your Server's IP

On the server:
```bash
hostname -I
# Expected: 192.168.1.100
```

On your phone, open browser and navigate to:
```
http://192.168.1.100:8080/health
```

You should see: `{"healthy": true, ...}`

### Step 3: Pair a New Device

From the server terminal:

```bash
# Pair a device with observe-only capability
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe

# Pair a device with full control
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

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

### Step 4: Verify Pairing

```bash
# List paired devices
cd services/home-miner-daemon
python3 cli.py events --kind pairing_granted --limit 5
```

## Opening the Command Center

### Option 1: Direct HTML File

Copy `apps/zend-home-gateway/index.html` to your phone or serve it:

```bash
# Serve the HTML file (on the server)
cd /opt/zend
python3 -m http.server 8000 --directory apps/zend-home-gateway
```

Then on your phone, open: `http://192.168.1.100:8000/index.html`

### Option 2: Copy File to Phone

Transfer `apps/zend-home-gateway/index.html` to your phone using:
- SCP/SFTP
- AirDrop
- Email
- USB cable

Open the file directly in your mobile browser.

### Configuring the Gateway URL

By default, the command center connects to `http://127.0.0.1:8080`. To connect to your home miner:

1. Open `index.html` in a text editor
2. Find the line:
   ```javascript
   const API_BASE = 'http://127.0.0.1:8080';
   ```
3. Change it to your server's IP:
   ```javascript
   const API_BASE = 'http://192.168.1.100:8080';
   ```
4. Save and open in browser

### Command Center Features

| Screen | Description |
|--------|-------------|
| **Home** | Miner status, mode switcher, quick actions |
| **Inbox** | Operations inbox (pairing, control receipts) |
| **Agent** | Hermes connection status |
| **Device** | Device info, permissions |

## Daily Operations

### Checking Status

```bash
# Via CLI
cd services/home-miner-daemon
python3 cli.py status

# Via curl
curl http://localhost:8080/status | python3 -m json.tool
```

### Changing Mining Mode

```bash
# Pause mining
python3 cli.py control --client my-phone --action stop

# Balanced mode (50 kH/s simulated)
python3 cli.py control --client my-phone --action set_mode --mode balanced

# Performance mode (150 kH/s simulated)
python3 cli.py control --client my-phone --action set_mode --mode performance
```

### Viewing Events

```bash
# All events
python3 cli.py events --limit 20

# Only control receipts
python3 cli.py events --kind control_receipt --limit 10

# Only pairing events
python3 cli.py events --kind pairing_granted --limit 5
```

### Starting/Stopping via Command Center

In the command center UI:

1. **Home screen** → Tap mode buttons (Paused/Balanced/Performance)
2. **Home screen** → Tap Start Mining or Stop Mining buttons

## Recovery

### State Corruption

If the daemon fails to start or behaves unexpectedly:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup current state
cp -r state state.backup

# Clear state directory
rm -rf state/*

# Restart
./scripts/bootstrap_home_miner.sh

# Re-pair devices
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Daemon Won't Start

**Port already in use:**
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process
sudo kill <PID>

# Or use a different port
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

**Python not found:**
```bash
# Check Python installation
which python3
python3 --version

# Install if missing
sudo apt install python3
```

**Permission denied:**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Check state directory permissions
ls -la state/
sudo chown -R $USER:$USER state/
```

### Viewing Logs

The daemon outputs to stdout. If running via systemd:

```bash
sudo journalctl -u zend -f
```

If running directly:
```bash
./scripts/bootstrap_home_miner.sh 2>&1 | tee daemon.log
```

### Resetting Everything

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove all state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh

# Re-pair devices
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Security

### LAN-Only By Default

Zend is designed for local network use only. By default:
- Daemon binds to `127.0.0.1` (localhost only)
- No encryption on the HTTP API
- No authentication (relies on network-level access control)

### Recommendations

| Do | Don't |
|----|-------|
| Run on a trusted LAN | Expose to the internet directly |
| Use a firewall to block port 8080 from outside | Set `ZEND_BIND_HOST=0.0.0.0` without firewall |
| Keep software updated | Ignore security advisories |
| Use observe-only for untrusted devices | Grant control to devices you don't trust |
| Monitor logs for unusual activity | Disable logging |

### Accessing Remotely (Advanced)

For remote access, use a secure tunnel:

```bash
# Using SSH tunnel (from your phone/client)
ssh -L 8080:localhost:8080 user@192.168.1.100

# Then connect to http://localhost:8080
```

Or use a VPN to access your home network securely.

### Firewall Setup

```bash
# Allow local access only (iptables)
sudo iptables -A INPUT -p tcp --dport 8080 -s 192.168.0.0/16 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP

# Verify rules
sudo iptables -L -n | grep 8080
```

### Updating Zend

```bash
cd /opt/zend

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup state
cp -r state state.backup

# Pull latest code
git pull

# Restart
./scripts/bootstrap_home_miner.sh
```
