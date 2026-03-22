# Operator Quickstart

This guide helps you deploy Zend on home hardware — a Raspberry Pi, mini PC, or any
Linux machine on your home network.

## Hardware Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| CPU | Any x86-64 or ARM | Dual-core |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB free | 4 GB free |
| OS | Linux (any) | Raspberry Pi OS, Ubuntu Server |
| Python | 3.10+ | 3.10+ |
| Network | Ethernet or WiFi | Ethernet |

Zend uses the Python standard library only. No GPU, no specialized mining hardware.

## Installation

### 1. Clone the Repository

SSH into your home server and clone the repository:

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or higher
```

If you need Python 3.10 on Raspberry Pi:

```bash
sudo apt update
sudo apt install python3.10-venv python3-pip
```

## Configuration

### Environment Variables

Create a configuration file:

```bash
cat > /opt/zend/.env << 'EOF'
# Bind to LAN interface (replace with your server's IP)
ZEND_BIND_HOST=0.0.0.0

# Daemon port
ZEND_BIND_PORT=8080

# State directory
ZEND_STATE_DIR=/opt/zend/state
EOF
```

### Load Configuration

```bash
set -a
source /opt/zend/.env
set +a
```

Or add to your shell profile (`~/.bashrc` or `~/.profile`):

```bash
echo 'export ZEND_BIND_HOST=0.0.0.0' >> ~/.bashrc
echo 'export ZEND_BIND_PORT=8080' >> ~/.bashrc
echo 'export ZEND_STATE_DIR=/opt/zend/state' >> ~/.bashrc
source ~/.bashrc
```

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
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
[INFO] Bootstrap complete
```

### Verify Health

```bash
curl http://localhost:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

## Pairing a Phone

### 1. Find Your Server's LAN IP

On the server:

```bash
hostname -I
```

Example output: `192.168.1.100`

### 2. Pair from Your Phone

Open a terminal on your phone (or use an SSH client) and run:

```bash
export ZEND_DAEMON_URL=http://192.168.1.100:8080
cd /opt/zend
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:05:00+00:00"
}
paired my-phone
capability=observe,control
```

### 3. Verify Pairing

```bash
python3 services/home-miner-daemon/cli.py events --client my-phone
```

You should see pairing_granted events.

## Opening the Command Center

### From Your Phone's Browser

1. Ensure your phone is on the same network as the server
2. Open your browser and navigate to:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

If this doesn't work, the daemon isn't serving static files. Instead, open the
file directly:

1. On the server, find the index.html path:

```bash
realpath /opt/zend/apps/zend-home-gateway/index.html
```

2. On your phone, open:

```
file:///opt/zend/apps/zend-home-gateway/index.html
```

Or serve it with Python:

```bash
cd /opt/zend/apps/zend-home-gateway
python3 -m http.server 8081
```

Then on your phone: `http://192.168.1.100:8081/index.html`

### Configure the Gateway URL

The command center expects the daemon at `http://127.0.0.1:8080`. To connect to
your server:

1. Open the JavaScript console in your browser
2. Run:

```javascript
localStorage.setItem('zend_daemon_url', 'http://192.168.1.100:8080');
location.reload();
```

Or edit the index.html file and change:

```javascript
const API_BASE = 'http://127.0.0.1:8080';
```

to:

```javascript
const API_BASE = 'http://192.168.1.100:8080';
```

## Daily Operations

### Check Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Change Mining Mode

```bash
# Pause mining
./scripts/set_mining_mode.sh --client my-phone --mode paused

# Balanced mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Performance mode
./scripts/set_mining_mode.sh --client my-phone --mode performance
```

### View Events

```bash
# Recent events
python3 services/home-miner-daemon/cli.py events --limit 20

# Control receipts only
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Recovery

### State Corruption

If the daemon won't start or reports errors:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf /opt/zend/state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

Check if the port is in use:

```bash
lsof -i :8080
```

Kill any existing process:

```bash
kill <PID>
```

Or restart:

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Stuck Process

If the daemon is unresponsive:

```bash
# Find PID
cat /opt/zend/state/daemon.pid

# Force kill
kill -9 <PID>
```

### Full Reset

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf /opt/zend/state/*
./scripts/bootstrap_home_miner.sh
```

Re-pair your devices:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Security

### LAN-Only Binding

The daemon binds to your LAN interface by default. It does not expose any ports
to the internet. Keep `ZEND_BIND_HOST=0.0.0.0` or your private IP — never
`0.0.0.0` on a public interface.

### Firewall

If you have a firewall, allow inbound on port 8080 from your local network:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

### What Not to Expose

- Do not forward port 8080 to the internet
- Do not bind to `0.0.0.0` on a public VPS
- Do not use the daemon with untrusted devices on public WiFi

### Authentication

Currently, authentication is device-name based with capability scopes. For
production, add token-based authentication (future feature).

## Service Setup (Optional)

Run Zend as a systemd service:

```bash
sudo cat > /etc/systemd/system/zend.service << 'EOF'
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend/state"
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend
```

Check status:

```bash
sudo systemctl status zend
```

View logs:

```bash
journalctl -u zend -f
```
