# Operator Quickstart

Deploy Zend on home hardware. This guide walks through installation, configuration, first boot, and daily operations.

## Hardware Requirements

- Any Linux machine with Python 3.10+
- Raspberry Pi 4 or similar is sufficient
- 1 GB free disk space
- Network access (same LAN as your phone)

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or later
```

No pip install. No other dependencies.

## Configuration

Environment variables control daemon behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind. Use your LAN IP (e.g., `192.168.1.100`) for remote access. |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `state/` | Directory for daemon state |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL (for CLI commands) |

### LAN Access (Recommended)

To access the command center from your phone on the same network:

```bash
# Find your LAN IP
hostname -I | awk '{print $1}'

# Start daemon bound to LAN interface
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

Replace `192.168.1.100` with your actual LAN IP.

## First Boot

### 1. Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Stopping Zend Home Miner Daemon
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

### 2. Open the Command Center

The command center is a single HTML file. The daemon does not serve it over HTTP — open it directly in your browser:

```bash
open apps/zend-home-gateway/index.html
```

Or navigate to:
- Local: `file:///path/to/zend/apps/zend-home-gateway/index.html`
- On your phone (same LAN): copy the file to your phone or serve it with any static file server, e.g. `python3 -m http.server 8081` from the repo root

### 3. Verify Connection

The status hero should show current miner state. If it shows "Unable to connect", check:

1. Is the daemon running? (`./scripts/bootstrap_home_miner.sh --status`)
2. Is the daemon bound to the right interface?
3. Is your browser accessing the correct URL?

## Pairing a Phone

### 1. Access the Command Center from Your Phone

Connect your phone to the same network. Open the command center URL in your browser.

### 2. Pair via CLI (on the server)

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

This creates a pairing record with `observe` and `control` capabilities.

### 3. Verify Pairing

```bash
python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted
```

You should see a pairing_granted event in the output.

## Daily Operations

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Change Mining Mode

```bash
# Pause mining
./scripts/set_mining_mode.sh --client my-phone --mode paused

# Balanced (medium hashrate)
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Performance (high hashrate)
./scripts/set_mining_mode.sh --client my-phone --mode performance
```

### Start/Stop Mining

```bash
./scripts/set_mining_mode.sh --client my-phone --action start
./scripts/set_mining_mode.sh --client my-phone --action stop
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt
```

### View Daemon Health

```bash
curl http://127.0.0.1:8080/health
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Recovery

### State Becomes Corrupt

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

Note: This deletes all pairing records and principal identity. You will need to re-pair devices.

### Daemon Won't Start

1. Check if the port is already in use:
   ```bash
   lsof -i :8080
   ```

2. Kill any existing process on that port, or change the port:
   ```bash
   ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
   ```

3. Check the daemon log (it prints to stdout/stderr):
   ```bash
   # Run in foreground to see logs
   python3 services/home-miner-daemon/daemon.py
   ```

### Pairing Token Expired

The daemon currently does not enforce token expiration in milestone 1. If you need to reset pairing:

```bash
# Remove specific device
rm state/pairing-store.json  # then re-pair

# Or clear all state
rm -rf state/* && ./scripts/bootstrap_home_miner.sh
```

## Security

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. This means only processes on the same machine can access it.

### Enabling LAN Access

When you bind to a LAN IP, the daemon is accessible to all devices on your network. Consider:

- Using a firewall to restrict access
- Not exposing the daemon to the internet
- Using a VPN for remote access instead of port forwarding

### What Not to Expose

- Do not expose `ZEND_BIND_HOST=0.0.0.0` on a public-facing server
- Do not use port forwarding to access the daemon from the internet
- Do not store sensitive data in the state directory without encryption

### Current Limitations

- No TLS/SSL in milestone 1
- No authentication beyond capability-scoped pairing
- No encryption of the event spine at rest (future milestone)

## Service Management

### Run as a Systemd Service

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/zend
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
ExecStart=/usr/bin/python3 /path/to/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home
```

### View Service Logs

```bash
sudo journalctl -u zend-home -f
```

## Troubleshooting

### "Unable to connect to Zend Home"

1. Verify daemon is running:
   ```bash
   curl http://127.0.0.1:8080/health
   ```

2. Check the correct URL in your browser:
   - Local: Use the file path
   - LAN: Use `http://<server-ip>:8080/apps/zend-home-gateway/index.html`

3. Check firewall rules on the server:
   ```bash
   sudo ufw allow 8080/tcp
   ```

### Status Shows "stale"

The status snapshot has an old freshness timestamp. This means the daemon hasn't received a fresh update. This is expected in milestone 1 with the simulator.

### Control Commands Fail with "unauthorized"

The device lacks the `control` capability. Pair again with:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Daemon Uses High CPU

In milestone 1, the simulator may use CPU for timing loops. This is expected. Real miner backends will not have this behavior.
