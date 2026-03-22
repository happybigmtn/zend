# Operator Quickstart

This guide walks you through deploying Zend on home hardware. Follow these steps to get a running system in under 10 minutes.

## Hardware Requirements

- **Minimum**: Any Linux system with Python 3.10+
- **Recommended**: Raspberry Pi 4 (4GB+), or a small home server
- **Storage**: 100MB for the repo, negligible for state files
- **Network**: Local network access (same subnet as your phone)

Zend is designed to run on modest hardware. It uses no GPU, requires no heavy dependencies, and the daemon uses minimal memory.

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python Version

```bash
python3 --version
# Must be Python 3.10 or higher
```

### 3. No pip Install Needed

Zend uses Python's standard library only. No external packages to install.

## Configuration

The daemon is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `<repo-root>/state` | Where state files are stored (default is relative to the daemon script, not cwd) |
| `ZEND_BIND_HOST` | `127.0.0.1` | Network interface to bind |
| `ZEND_BIND_PORT` | `8080` | Port for the HTTP server |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Full daemon URL for CLI |

### LAN-Only Binding

For home deployment, bind to your LAN interface:

```bash
# Find your LAN IP
ip addr show | grep inet

# Example output:
# inet 192.168.1.100/24 brd 192.168.1.255 scope global wlan0

# Set the bind address
export ZEND_BIND_HOST=192.168.1.100
export ZEND_BIND_PORT=8080
```

**Warning**: Never bind to `0.0.0.0` in phase 1. This exposes the control surface to your entire network. Bind to a specific IP.

## First Boot

### Start the Daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

**Expected output:**
```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
[INFO] Bootstrap complete
```

### Verify Daemon is Running

```bash
curl http://192.168.1.100:8080/health
```

**Expected output:**
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

**Expected output:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

## Pairing a Phone

### 1. Serve the Command Center

On the server, serve the gateway UI:

```bash
cd /opt/zend/apps/zend-home-gateway
python3 -m http.server 3000
```

### 2. Open on Your Phone

Open your phone's browser and navigate to:

```
http://192.168.1.100:3000
```

You should see the Zend Home command center with the Status Hero showing "Stopped".

### 3. Test the UI

- The Status Hero shows miner state (stopped/running)
- The Mode Switcher has three options: Paused, Balanced, Performance
- The Quick Actions have Start Mining and Stop Mining buttons

If you see data, the pairing is working. The default pairing (`alice-phone`) is created during bootstrap.

### Pairing Additional Devices

To pair another device with control capability:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

**Output:**
```
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:05:00+00:00"
}

paired my-phone
capability=observe,control
```

## Daily Operations

### Check Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Via HTTP
curl http://192.168.1.100:8080/status
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action start
```

**Expected output:**
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

### Change Mining Mode

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

Modes:
- `paused`: No mining, minimum power
- `balanced`: Moderate hashrate (~50 kH/s)
- `performance`: Full hashrate (~150 kH/s)

### View Events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 20
```

This shows recent events from the event spine: pairing approvals, control receipts, alerts.

## Auto-Start on Boot

### systemd Service

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment=ZEND_BIND_HOST=192.168.1.100
Environment=ZEND_BIND_PORT=8080
Environment=ZEND_STATE_DIR=/opt/zend/state
ExecStart=/opt/zend/scripts/bootstrap_home_miner.sh --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend-home
sudo systemctl start zend-home
sudo systemctl status zend-home
```

## Recovery

### State is Corrupted

If the daemon fails to start or state seems wrong:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove corrupted state
rm -rf state/*

# Restart fresh
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

Check if another process is using the port:

```bash
# Find what's using port 8080
lsof -i :8080
# or
ss -tlnp | grep 8080

# Kill the process if needed
kill <PID>
```

### CLI Can't Connect

Verify the daemon is running and the URL is correct:

```bash
# Check daemon health
curl http://192.168.1.100:8080/health

# Set correct URL for CLI
export ZEND_DAEMON_URL=http://192.168.1.100:8080
python3 services/home-miner-daemon/cli.py status
```

### Re-pairing a Device

There is no update path for an existing device — `pair_client` raises `ValueError` for duplicate device names. To re-pair:

```bash
# Stop the daemon first
./scripts/bootstrap_home_miner.sh --stop

# Remove all state (wipes principal, pairings, and event log)
rm -rf state/*

# Restart fresh
./scripts/bootstrap_home_miner.sh
```

## Security

### LAN-Only Access

The daemon binds to your LAN IP, not the internet. It is not accessible from outside your network.

### No Authentication by Default

Phase 1 relies on network-level isolation. Anyone on your LAN can access the daemon if they know the IP and port.

**For additional security in phase 1:**
- Use a strong WiFi password
- Consider MAC address filtering
- Place the miner on a guest network if your router supports it

**Note on token expiry:** The pairing token's `expires` field is set to the current time at creation (store.py:57-58) — there is no TTL enforcement. The claim of "24-hour expiry" is not yet implemented. Do not rely on token expiry as a security control.

### What Not to Expose

- Do not port-forward port 8080 to the internet
- Do not bind to `0.0.0.0` (all interfaces)
- Do not run the daemon as root

### Future Security

Phase 2 will add:
- Token-based authentication
- TLS encryption
- Remote access via secure tunnel

## Troubleshooting

### "Unable to connect to Zend Home"

The daemon isn't running or the UI can't reach it.

1. Verify daemon is running:
   ```bash
   curl http://192.168.1.100:8080/health
   ```

2. Verify the HTTP server is running for the UI:
   ```bash
   lsof -i :3000
   ```

3. Check your phone is on the same network

### "This device lacks 'control' capability"

Your paired device only has `observe` permission.

1. Pair with control capability:
   ```bash
   ./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
   ```

### Miner won't start

1. Check status:
   ```bash
   curl http://192.168.1.100:8080/status
   ```

2. Check daemon logs (no logs file yet in milestone 1; daemon output goes to terminal)

3. Try stopping and starting:
   ```bash
   ./scripts/bootstrap_home_miner.sh --stop
   ./scripts/bootstrap_home_miner.sh
   ```

### High CPU usage

The miner simulator should use minimal CPU. If you see high usage:

1. Check for runaway processes:
   ```bash
   top
   ```

2. The daemon is single-threaded. High CPU would indicate an issue.

## State Files Reference

| File | Purpose |
|------|---------|
| `state/principal.json` | Your Zend identity |
| `state/pairing-store.json` | All paired devices |
| `state/event-spine.jsonl` | Audit log of all operations |
| `state/daemon.pid` | Daemon process ID |

These files are small (KB range) and safe to back up. They contain no sensitive secrets.

## Next Steps

- Read [Architecture](architecture.md) to understand the system design
- Read [API Reference](api-reference.md) to understand the daemon API
- Read the [Product Spec](../specs/2026-03-19-zend-product-spec.md) to understand the vision
