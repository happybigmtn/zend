# Operator Quickstart — Home Hardware Deployment

This guide gets you from a fresh Linux machine to a running Zend Home Miner
daemon on home hardware. No cloud services. No internet-facing control surfaces.
Everything stays on your LAN.

**Target hardware:** any Linux machine (Raspberry Pi, old desktop, NAS, etc.)
with Python 3.10+ and a LAN connection.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any ARMv7 or x86_64 | 4+ cores |
| RAM | 256 MB | 1 GB+ |
| Storage | 100 MB free | 1 GB+ free |
| Network | Ethernet or Wi-Fi on LAN | Ethernet |
| OS | Linux (Raspbian, Ubuntu, Debian) | Latest LTS |

Python 3.10+ is required. No other runtime dependencies.

## Step 1 — Install Python

Most modern Linux distributions include Python 3.10+. Check:

```bash
python3 --version
```

If the version is below 3.10, install it:

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install -y python3
```

## Step 2 — Clone the Repository

On your home hardware machine:

```bash
git clone <repo-url> /opt/zend-home && cd /opt/zend-home
```

Or, if you already have the repo:

```bash
cd /path/to/zend
```

## Step 3 — Configure the Daemon

The daemon binds to a LAN interface by default. Set your machine's LAN IP
before starting:

```bash
# Find your LAN IP
hostname -I | awk '{print $1}'

# Example: your machine is 192.168.1.100
export ZEND_BIND_HOST="192.168.1.100"
export ZEND_BIND_PORT="8080"
export ZEND_STATE_DIR="/opt/zend-home/state"
```

For a permanent configuration, add these to your shell profile:

```bash
echo 'export ZEND_BIND_HOST="192.168.1.100"' >> ~/.bashrc
echo 'export ZEND_BIND_PORT="8080"' >> ~/.bashrc
echo 'export ZEND_STATE_DIR="/opt/zend-home/state"' >> ~/.bashrc
source ~/.bashrc
```

## Step 4 — Bootstrap the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Daemon started (PID: 1234)
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
Bootstrap complete
```

The daemon is now listening on your LAN IP. Verify:

```bash
curl http://192.168.1.100:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Step 5 — Access the Command Center from Your Phone

The command center is a single HTML file. To open it from your phone's browser:

1. Make sure your phone is on the same LAN as the daemon machine.
2. Navigate to: `http://192.168.1.100:8080/`

   (The daemon serves `apps/zend-home-gateway/index.html` at the root path.)

3. The UI should show the Zend Home command center.

**Troubleshooting:**
- If the page doesn't load, check that your phone is on the same network.
- If `curl` works but the browser doesn't, check for captive portal or VPN
  interference on the phone.

## Step 6 — Pair Your Phone

From your **development machine** (or the daemon machine), run:

```bash
# Pair with observe-only capability
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe

# Or pair with control capability (can change modes)
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T00:00:00Z"
}
paired my-phone
capability=observe,control
```

The pairing record is stored in `state/pairing-store.json`.

## Daily Operations

### Check Miner Status

```bash
curl http://192.168.1.100:8080/status
```

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "freshness": "2026-03-22T00:00:00Z"
}
```

### Start Mining

```bash
curl -X POST http://192.168.1.100:8080/miner/start
# {"success": true, "status": "running"}
```

### Stop Mining

```bash
curl -X POST http://192.168.1.100:8080/miner/stop
# {"success": true, "status": "stopped"}
```

### Change Mining Mode

```bash
curl -X POST http://192.168.1.100:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
# {"success": true, "mode": "balanced"}
```

Valid modes: `paused`, `balanced`, `performance`

### View Events (Spine)

```bash
python3 services/home-miner-daemon/cli.py events --client my-phone --kind all --limit 20
```

## Recovery

### State Becomes Corrupt

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

This creates a new `PrincipalId`. Any previously paired clients must be re-paired.

### Daemon Won't Start (Port Already in Use)

```bash
# Find what's using the port
sudo lsof -i :8080

# Kill it or use a different port
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

Then update your phone's command-center URL to the new port.

### Daemon Crashes

The daemon writes a PID file at `state/daemon.pid`. If it crashes:

```bash
# Clean up stale PID file
rm -f state/daemon.pid

# Restart
./scripts/bootstrap_home_miner.sh
```

### Phone Can't Reach the Daemon

1. Verify the daemon is running: `curl http://192.168.1.100:8080/health`
2. Verify the phone is on the same LAN: `ping 192.168.1.100`
3. Check the firewall on the daemon machine:

   ```bash
   # Allow port 8080 on the LAN interface (Ubuntu/Debian)
   sudo ufw allow from 192.168.1.0/24 to any port 8080
   ```

## Security

### LAN-Only by Design

Milestone 1 daemon does **not** expose control surfaces to the internet. It binds
to the private LAN interface only. Do not change `ZEND_BIND_HOST` to `0.0.0.0`
or a public IP in milestone 1.

### What Not to Expose

- The daemon port (8080) should not be port-forwarded to the internet
- The `state/` directory contains pairing tokens and principal identity — treat
  it as sensitive local data
- The event spine (`state/event-spine.jsonl`) contains operational history —
  it is append-only and local

### Pairing Tokens

Pairing tokens are currently not time-limited in milestone 1. Token expiration
(`ZEND_TOKEN_TTL_HOURS`) is planned for a future milestone. Until then,
revocation requires deleting the pairing record from `state/pairing-store.json`:

```bash
# List current pairings
python3 -c "
import json
with open('state/pairing-store.json') as f:
    for k, v in json.load(f).items():
        print(f'{v[\"device_name\"]}: {k}')
"

# Manually remove a pairing (edit the JSON)
nano state/pairing-store.json
```

## Background Startup

To run the daemon as a persistent background service on Linux using systemd:

```bash
sudo nano /etc/systemd/system/zend-home.service
```

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/opt/zend-home
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend-home/state"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home

# Check status
sudo systemctl status zend-home

# View logs
journalctl -u zend-home -f
```

## Service URL Reference

| Service | URL |
|---------|-----|
| Health check | `http://<HOST>:8080/health` |
| Miner status | `http://<HOST>:8080/status` |
| Command center UI | `http://<HOST>:8080/` |
