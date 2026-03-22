# Operator Quickstart

Deploy and operate Zend on home hardware. This guide assumes a Linux system (including Raspberry Pi).

## Hardware Requirements

- **CPU**: Any Linux-capable ARM or x86 processor
- **RAM**: 256 MB minimum (Python stdlib is lightweight)
- **Storage**: 100 MB for repository + state
- **Network**: Ethernet or WiFi (LAN connectivity required)
- **OS**: Linux (tested on Raspberry Pi OS, Ubuntu, Debian)

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be Python 3.10 or higher
```

No pip packages needed. No build step. No containerization required.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `./state` | State directory |

### LAN Binding (Recommended for Home Deployment)

To access the daemon from other devices on your network:

```bash
# Get your LAN IP
hostname -I

# Start daemon with LAN binding
ZEND_BIND_HOST=0.0.0.0 ./scripts/bootstrap_home_miner.sh
```

This binds the daemon to all network interfaces. Your phone can then access the gateway.

### Custom Port

```bash
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

## First Boot

### Run Bootstrap

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
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

### Verify Daemon Health

```bash
curl http://127.0.0.1:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
curl http://127.0.0.1:8080/status
```

Expected:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 5,
  "freshness": "2026-03-22T12:00:05Z"
}
```

## Pairing a Phone

### Step 1: Find Your Daemon IP

On the server:

```bash
hostname -I
# Example output: 192.168.1.100
```

### Step 2: Open Gateway on Phone

On your phone's browser, navigate to:

```
http://192.168.1.100:8080/apps/zend-home-gateway/index.html
```

Or copy `apps/zend-home-gateway/index.html` to your phone and open it directly.

### Step 3: Update Gateway URL (if needed)

If the gateway can't connect, edit the `API_BASE` constant in the HTML file:

```javascript
// Change from:
const API_BASE = 'http://127.0.0.1:8080';

// To your server IP:
const API_BASE = 'http://192.168.1.100:8080';
```

### Step 4: Verify Connection

You should see:
- Miner status (stopped/paused)
- Mode switcher
- Start/Stop buttons

If you see "Unable to connect to Zend Home", check:
- Daemon is running on server
- Phone is on same network
- Firewall allows port 8080

## Daily Operations

### Check Status

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py status

# Via HTTP
curl http://127.0.0.1:8080/status
```

### Start Mining

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Via HTTP
curl -X POST http://127.0.0.1:8080/miner/start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Change Mining Mode

```bash
# Pause
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode paused

# Balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Performance
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode performance
```

### View Event Log

```bash
# Recent events
python3 services/home-miner-daemon/cli.py events --limit 20

# All events
python3 services/home-miner-daemon/cli.py events --limit 100

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

## Recovery

### Daemon Won't Start

```bash
# Check if port is already in use
lsof -i :8080

# Kill existing process
kill <PID>

# Or use a different port
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

### State Corruption

If you see errors about corrupted state:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Backup old state (optional)
mv state state.old

# Re-bootstrap (creates fresh state)
./scripts/bootstrap_home_miner.sh
```

### Gateway Can't Connect

1. Verify daemon is running:
   ```bash
   curl http://127.0.0.1:8080/health
   ```

2. Check the daemon is bound to the right interface:
   ```bash
   # For LAN access, should be 0.0.0.0
   # For local only, should be 127.0.0.1
   netstat -tlnp | grep 8080
   ```

3. Check firewall:
   ```bash
   # Allow port 8080
   sudo ufw allow 8080/tcp
   ```

### Reset Everything

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove all state
rm -rf state/

# Fresh start
./scripts/bootstrap_home_miner.sh
```

## Security Notes

### LAN-Only by Default

The daemon binds to `127.0.0.1` by default. This means only processes on the same machine can connect.

### LAN Deployment

When you bind to `0.0.0.0`:

- Devices on your LAN can reach the daemon
- **Do not expose port 8080 to the internet**
- Use a VPN or SSH tunnel for remote access
- Consider firewall rules to restrict access

### No Authentication in Milestone 1

Current milestone does not include:
- API authentication
- Encrypted connections
- Token validation

For home LAN use, this is acceptable. Future milestones will add security.

### Recommendations

1. **Isolate your mining network**: Don't put this on a shared network
2. **Use firewall rules**: Only allow devices you trust
3. **No internet exposure**: Keep port 8080 LAN-only
4. **Monitor access**: Check `state/event-spine.jsonl` for unusual activity

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or manually:

```bash
# Find PID
lsof -i :8080

# Kill
kill <PID>
```

## Troubleshooting Checklist

- [ ] Python 3.10+ installed
- [ ] Daemon started successfully (no error messages)
- [ ] `curl http://127.0.0.1:8080/health` returns JSON
- [ ] Phone on same network as server
- [ ] Gateway URL points to correct IP
- [ ] Port 8080 not blocked by firewall
- [ ] State directory exists and is writable

## Next Steps

- Read [API Reference](api-reference.md) for all available endpoints
- Read [Architecture](architecture.md) to understand the system
- Review [Design System](../DESIGN.md) for UI customization
