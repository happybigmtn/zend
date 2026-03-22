# Operator Quickstart — Zend Home on Home Hardware

This guide deploys Zend Home on a personal Linux machine: a home server, a NAS, a
Raspberry Pi, or any spare Linux box. No cloud account. No internet exposure. The
daemon runs on your LAN only.

**Time to working system:** Under 10 minutes on a typical home network.

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Any x86_64 or ARMv7+ | ARMv8 (Raspberry Pi 3B+ or better) |
| RAM | 256 MB | 512 MB |
| Disk | 100 MB free | 1 GB free |
| OS | Linux (any distribution) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet or Wi-Fi LAN | Ethernet |
| Python | 3.10 or later | Same |

Most Raspberry Pi models running Raspberry Pi OS work out of the box. Tested
configurations: Raspberry Pi 3B+, Raspberry Pi 4, and generic x86_64 Linux VMs.

## Installation

### 1. Install Python 3.10+

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y python3 python3-pytest git curl

# Raspberry Pi OS (Debian-based)
sudo apt-get update
sudo apt-get install -y python3 python3-pytest git curl

# Verify
python3 --version
```

### 2. Clone the Repository

```bash
git clone <repo-url> /opt/zend-home
cd /opt/zend-home
```

Keep the repository in a stable location. The `state/` directory (where runtime
data lives) is in `.gitignore` — it will be created automatically.

### 3. Configure (Optional)

Environment variables control daemon behavior. Set them before running the
bootstrap script.

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `<repo>/state` | Where runtime state is stored |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` for LAN access from other machines |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Full URL (used by CLI and HTML gateway) |

To allow the HTML command center on your phone to access the daemon from another
machine on the LAN:

```bash
# Bind to all LAN interfaces (including Ethernet/Wi-Fi)
export ZEND_BIND_HOST=0.0.0.0

# Or bind to a specific LAN IP
export ZEND_BIND_HOST=192.168.1.100
```

## First Boot

### 1. Start the Daemon

```bash
cd /opt/zend-home
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
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

The daemon is now running. Take note of the `principal_id` — it is your Zend
installation's stable identity. It is stored in `state/principal.json`.

### 2. Open the Command Center

**On the same machine:**

```bash
# Open directly in the default browser
xdg-open apps/zend-home-gateway/index.html
# or
open apps/zend-home-gateway/index.html   # macOS
```

**On a phone or tablet on the same LAN** (requires `ZEND_BIND_HOST=0.0.0.0`):

1. Find the machine's LAN IP: `hostname -I | awk '{print $1}'`
2. Open `http://<machine-ip>:8080/status` in a browser to verify the daemon is reachable
3. Open `file:///opt/zend-home/apps/zend-home-gateway/index.html` from the phone's
   file manager, or serve it via a simple HTTP server on the machine

For a simple local server on the machine:

```bash
cd /opt/zend-home
python3 -m http.server 8081 --directory apps/zend-home-gateway
# Phone: open http://<machine-ip>:8081/index.html
```

The command center shows:
- **Home tab**: live miner status, mode switcher, start/stop buttons
- **Inbox tab**: pairing approvals, control receipts, alerts, Hermes summaries
- **Agent tab**: Hermes connection status
- **Device tab**: paired device name, permissions (observe/control)

## Pairing a Phone

The bootstrap script already paired a default device named `alice-phone` with
`observe` capability. To pair your phone with `control` capability:

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

If the device name already exists, pairing fails with an error. Use a unique name
per device.

## Daily Operations

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Returns the current status, mode, hashrate, temperature, uptime, and freshness
timestamp.

### Change Mining Mode

```bash
# Switch to balanced mode
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action set_mode --mode balanced

# Start mining (in the current mode)
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action stop
```

If the device lacks `control` capability, the command fails with `unauthorized`.

### View Event History

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone \
  --kind control_receipt --limit 10
```

### View Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

Returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": ...}`.

### Check If Daemon Is Running

```bash
# Via PID file
cat state/daemon.pid
kill -0 $(cat state/daemon.pid) && echo "running" || echo "not running"

# Via HTTP
curl -s http://127.0.0.1:8080/health && echo "" || echo "daemon not responding"
```

## Recovery

### Daemon Won't Start (Port Already in Use)

```bash
# Find what's using port 8080
lsof -i :8080
# or
ss -tlnp | grep 8080

# Kill the process or change the port
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### State Is Corrupted or You Want a Clean Slate

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe all state (pairing records and events are deleted)
rm -rf state/*

# Re-bootstrap from scratch
./scripts/bootstrap_home_miner.sh
```

### Daemon Starts But HTML Command Center Can't Connect

1. Verify the daemon is running: `curl http://127.0.0.1:8080/health`
2. If `ZEND_BIND_HOST` is `127.0.0.1`, the daemon only accepts connections from
   the same machine. Set `ZEND_BIND_HOST=0.0.0.0` for LAN access.
3. If the phone is on Wi-Fi and the machine is on Ethernet, they may be on
   different subnets. Check with `ip addr` and `ip route`.
4. Check the phone's browser is not using a proxy.

### Pairing Script Fails

- **"already paired" error**: Use a different device name. Each device name is
  unique per installation.
- **"daemon unavailable"**: The daemon is not running. Run `bootstrap_home_miner.sh`
  first.
- **Permission denied**: The `state/` directory must be writable. Check:
  `ls -la state/` and `chmod u+w state/`.

## Security

**LAN-only by design.** In milestone 1, the daemon binds to your local network
only. It does not open any ports to the internet and does not support remote
access. This is intentional: it keeps blast radius small while proving the
product's control-plane thesis.

**Best practices for home deployment:**

1. **Use a firewall.** Most home routers provide NAT. The daemon should not
   receive connections from the internet regardless. Verify with
   `curl https://ifconfig.me` from outside your network — it should not connect.

2. **Keep the `state/` directory private.** Pairing records and event history
   are stored in plaintext JSON files in `state/`. On a multi-user system, ensure
   only your user can read and write `state/`:
   ```bash
   chmod -R 700 state/
   ```

3. **No secrets in environment variables.** `ZEND_BIND_HOST`, `ZEND_BIND_PORT`,
   etc. are not secret. The pairing tokens and principal identity are stored in
   files, not environment variables.

4. **Do not bind to `0.0.0.0` on a shared network.** If you are on a network
   with untrusted devices, bind to your specific LAN IP instead:
   ```bash
   export ZEND_BIND_HOST=192.168.1.100
   ```

5. **Monitor the event spine.** Events in `state/event-spine.jsonl` record every
   pairing, control action, and alert. An unexpected pairing event could indicate
   unauthorized access to your LAN.

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

This sends a SIGTERM to the daemon process. If the process does not stop cleanly
within 1 second, it is killed with SIGKILL.

## Auto-Start on Boot (systemd)

To start the daemon automatically when the machine boots:

```bash
sudo tee /etc/systemd/system/zend-home.service << 'EOF'
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend-home
ExecStart=/opt/zend-home/scripts/bootstrap_home_miner.sh --daemon
ExecStop=/opt/zend-home/scripts/bootstrap_home_miner.sh --stop
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home
```

Replace `User=pi` with your actual username.

Check status:
```bash
sudo systemctl status zend-home
```
