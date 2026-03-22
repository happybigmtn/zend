# Operator Quickstart

Deploy Zend on home hardware. This guide walks you through installation,
configuration, first boot, and daily operations.

## Hardware Requirements

- Any Linux box with Python 3.10+
- Recommended: Raspberry Pi 4 (4GB+) or similar single-board computer
- Network: Ethernet or WiFi on your local network
- Storage: 1GB free space (state files are minimal)
- RAM: 512MB minimum

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> && cd zend
```

No pip install needed. Zend uses Python stdlib only.

### 2. Verify Python

```bash
python3 --version  # Must be 3.10 or higher
```

If not available, install Python 3.10+:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install python3 python3-venv

# Raspberry Pi OS
sudo apt update && sudo apt install python3
```

## Configuration

Zend uses environment variables for configuration. Set these before starting:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Where state files are stored |
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address (see below) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |

### Binding Configuration

**For local access only** (default, most secure):

```bash
export ZEND_BIND_HOST=127.0.0.1
export ZEND_BIND_PORT=8080
```

**For LAN access** (phone can access daemon):

```bash
# Find your LAN IP first
hostname -I | awk '{print $1}'

# Set bind address to LAN IP
export ZEND_BIND_HOST=192.168.1.100  # Use your actual LAN IP
export ZEND_BIND_PORT=8080
```

**For all interfaces** (not recommended for production):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

### Persistent Configuration

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
echo 'export ZEND_BIND_HOST=192.168.1.100' >> ~/.bashrc
echo 'export ZEND_BIND_PORT=8080' >> ~/.bashrc
source ~/.bashrc
```

## First Boot

### 1. Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "660e8400-e29b-41d4-a716-446655440001",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
[INFO] Bootstrap complete
```

### 2. Verify Health

```bash
curl http://localhost:8080/health
```

Expected output:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 5
}
```

### 3. Check Status

```bash
curl http://localhost:8080/status
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 10,
  "freshness": "2026-03-22T10:30:10+00:00"
}
```

## Pairing a Phone

### 1. Find the Daemon URL

On your phone's browser, navigate to the daemon URL:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

### 2. Open the Command Center

The command center should load. If you see a pairing screen:

1. Enter a device name (e.g., "my-phone")
2. Grant `observe` capability (for status viewing)
3. Optionally grant `control` capability (for miner control)
4. Confirm the trust ceremony

### 3. Verify Pairing

On the daemon host:

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 30,
  "freshness": "2026-03-22T10:30:30+00:00"
}
```

## Daily Operations

### Check Miner Status

```bash
# From daemon host
python3 services/home-miner-daemon/cli.py status --client my-phone

# From any machine on LAN
curl http://192.168.1.100:8080/status
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
```

Expected output:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode performance
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

### View Event History

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Pairing events only
python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted

# Last 5 events
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 5
```

### Access the Command Center

Open in your phone's browser:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

The command center shows:
- **Home**: Live miner status, mode, temperature
- **Inbox**: Pairing approvals, control receipts, alerts
- **Agent**: Hermes integration status
- **Device**: Trust, pairing, permissions

## Recovery

### Daemon Won't Start

```bash
# Stop any existing daemon
./scripts/bootstrap_home_miner.sh --stop

# Check for port conflicts
lsof -i :8080

# Restart
./scripts/bootstrap_home_miner.sh
```

### State Corruption

If the daemon behaves unexpectedly, clear state and re-bootstrap:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

Note: This creates a new principal identity. Existing pairings will be invalid.

### Phone Can't Connect

1. Verify daemon is running:
   ```bash
   curl http://localhost:8080/health
   ```

2. Check firewall:
   ```bash
   # Allow port 8080
   sudo ufw allow 8080/tcp
   ```

3. Verify LAN connectivity:
   ```bash
   # From phone, try:
   ping 192.168.1.100
   ```

4. Check bind address:
   ```bash
   echo $ZEND_BIND_HOST  # Should be your LAN IP, not 127.0.0.1
   ```

### Verify No Mining on Phone

The daemon includes a proof that mining never happens on the client:

```bash
./scripts/no_local_hashing_audit.sh --client my-phone
```

Expected output:
```
checked: client process tree
checked: local CPU worker count
result: no local hashing detected
```

## Security

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default, preventing remote access.

To access from your phone, set `ZEND_BIND_HOST` to your LAN IP, but be aware:

- Anyone on your local network can access the daemon
- No authentication is required (pairing is your auth)
- Do not expose port 8080 to the internet

### Production Hardening

For production deployment:

1. **Use a firewall**: Only allow access from your phone's IP
2. **Consider TLS**: Add a reverse proxy with HTTPS
3. **Monitor logs**: Check for unauthorized access attempts
4. **Regular updates**: Keep the repo up to date

### What NOT to Do

- Don't bind to `0.0.0.0` on an internet-facing network
- Don't expose the daemon port to the internet
- Don't share pairing tokens with untrusted parties

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Address already in use" | Port 8080 occupied | Stop other process or change `ZEND_BIND_PORT` |
| "Daemon unavailable" | Daemon not running | Run `./scripts/bootstrap_home_miner.sh` |
| Phone can't connect | Wrong bind address | Set `ZEND_BIND_HOST` to LAN IP |
| Phone can't connect | Firewall blocking | Allow port 8080: `sudo ufw allow 8080/tcp` |
| "Unauthorized" error | Client not paired | Run bootstrap and pair again |
| "Invalid mode" error | Wrong mode value | Use `paused`, `balanced`, or `performance` |

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `./scripts/bootstrap_home_miner.sh` | Start daemon, create principal |
| `./scripts/bootstrap_home_miner.sh --stop` | Stop daemon |
| `./scripts/bootstrap_home_miner.sh --status` | Check daemon status |
| `./scripts/pair_gateway_client.sh` | Pair a new device |
| `./scripts/read_miner_status.sh` | Read miner status |
| `./scripts/set_mining_mode.sh` | Change mining mode |

## State Files

State is stored in `state/` (gitignored):

| File | Purpose |
|------|---------|
| `principal.json` | Your principal identity (keep private) |
| `pairing-store.json` | Paired devices and capabilities |
| `event-spine.jsonl` | Event history (append-only log) |
| `daemon.pid` | Daemon process ID |

Back up `state/` if you want to preserve identity across reinstalls.
