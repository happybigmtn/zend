# Operator Quickstart

This guide walks you through deploying Zend on home hardware. By the end, you'll have a running daemon, a paired phone, and the command center accessible from your browser.

## Hardware Requirements

- **CPU:** Any x86-64 or ARM processor (Raspberry Pi, old laptop, NAS)
- **RAM:** 256 MB minimum
- **Storage:** 100 MB for state files
- **OS:** Linux (Ubuntu, Debian, Raspberry Pi OS, etc.)
- **Network:** Ethernet or WiFi on your home network

Zend is designed to run on modest hardware. A Raspberry Pi 3 or newer works well.

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

Or for a local development setup:
```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or higher
```

If your system has an older Python version, install Python 3.10+:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update
sudo apt install python3
```

### 3. No pip Install Required

Zend uses only the Python standard library. No external packages to install.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_TOKEN_TTL_HOURS` | 24 | Pairing token TTL |

### LAN Access Configuration

By default, the daemon binds to `127.0.0.1` (localhost only). To access from your phone on the same network:

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

**Security Note:** Binding to `0.0.0.0` exposes the daemon on your LAN. Only do this if your network is trusted. Zend has no built-in authentication beyond device pairing.

## First Boot

### 1. Start the Daemon

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
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. The PID is saved to `state/daemon.pid`.

### 2. Verify Health

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Expected output:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T..."
}
```

## Pairing a Phone

The bootstrap script created a default pairing for `alice-phone` with `observe` capability. For full control, pair a new client with both `observe` and `control` capabilities.

### 1. Pair Your Phone

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T..."
}
paired my-phone
capability=observe,control
```

### 2. List Paired Devices

```bash
cat state/pairing-store.json
```

## Opening the Command Center

### For Local Development (Same Machine)

Open this file in your browser:
```
apps/zend-home-gateway/index.html
```

Or via the file protocol:
```
file:///opt/zend/apps/zend-home-gateway/index.html
```

### For Phone Access (Same Network)

1. Configure daemon for LAN access:
```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Start with LAN binding
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh
```

2. Find your machine's LAN IP:
```bash
hostname -I | awk '{print $1}'
# Example: 192.168.1.100
```

3. On your phone, open this URL in the browser:
```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

**Note:** This requires serving the HTML file. Alternatively, copy the HTML file to your phone or use a simple HTTP server:

```bash
# Serve the apps directory
cd apps
python3 -m http.server 8081
# Then access: http://192.168.1.100:8081/zend-home-gateway/index.html
```

### What You'll See

The command center shows:
- **Home:** Miner status, mode switcher, start/stop buttons, latest receipt
- **Inbox:** Operations receipts and alerts
- **Agent:** Hermes agent status (future feature)
- **Device:** Paired device info and permissions

The status hero shows the current miner state (running/stopped), hashrate, and freshness timestamp.

## Daily Operations

### Check Miner Status

**Via CLI:**
```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

**Via curl:**
```bash
curl http://127.0.0.1:8080/status
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
```

Or via script:
```bash
./scripts/set_mining_mode.sh --client my-phone --action start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

### Set Mining Mode

**Paused (no mining):**
```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode paused
```

**Balanced (moderate):**
```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

**Performance (maximum):**
```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode performance
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 10
```

## Mining Modes

| Mode | Simulated Hashrate | Use Case |
|------|-------------------|----------|
| `paused` | 0 H/s | Testing, maintenance |
| `balanced` | ~50 kH/s | Daily operation |
| `performance` | ~150 kH/s | Maximum output |

*Note: This is a milestone 1 simulator. Real hashrates will differ when connected to actual mining hardware.*

## Recovery

### Daemon Won't Start

**Check if already running:**
```bash
./scripts/bootstrap_home_miner.sh --status
```

**Kill and restart:**
```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

**Port conflict:**
```bash
lsof -i :8080
# Kill the conflicting process or change ZEND_BIND_PORT
```

### State Corruption

If the daemon behaves unexpectedly, reset the state:

```bash
# Backup existing state
mv state state.backup.$(date +%Y%m%d)

# Create fresh state
./scripts/bootstrap_home_miner.sh
```

### Pairing Lost

If your phone can't connect:

```bash
# Check pairing records
cat state/pairing-store.json

# Pair again if needed
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Daemon Crashes

Check the logs:
```bash
# Daemon output goes to stdout/stderr
# Check if daemon is running
ps aux | grep daemon.py

# Restart
./scripts/bootstrap_home_miner.sh
```

## Systemd Service (Optional)

For automatic startup on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/zend.service
```

```
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10
Environment=ZEND_BIND_HOST=0.0.0.0
Environment=ZEND_BIND_PORT=8080

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend
sudo systemctl status zend
```

## Security Notes

### Network Exposure

- **Default:** Daemon binds to `127.0.0.1` (localhost only)
- **LAN access:** Requires `ZEND_BIND_HOST=0.0.0.0`
- **Internet:** Never expose the daemon directly to the internet

### What to Check

1. **Firewall:** Ensure only trusted devices can reach port 8080 on your machine
2. **Router:** Don't port-forward 8080 to the internet
3. **Devices:** Only pair devices you control

### What Not to Expose

- The daemon has no built-in authentication
- Pairing tokens are stored in plaintext JSON
- Event spine contains operational details

Treat your home network as trusted, or add external authentication (VPN, reverse proxy with auth).

## Monitoring

### Check Daemon Health

```bash
curl http://127.0.0.1:8080/health
```

### View Event Spine

```bash
tail -f state/event-spine.jsonl
```

### Check State Files

```bash
ls -la state/
cat state/principal.json
```

## Updating

```bash
cd /opt/zend
git pull
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

Note: State files in `state/` are preserved between updates.

## Uninstall

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove state
rm -rf state

# Remove repository
cd ..
rm -rf zend
```

## Support

- Review `docs/architecture.md` for system design
- Check `references/` for architecture contracts
- See `docs/contributor-guide.md` for development info
