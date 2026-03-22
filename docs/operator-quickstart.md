# Operator Quickstart

This guide walks you through deploying Zend Home Miner on your own hardware. You'll run a daemon on a Linux machine and control it from your phone or another device on the same network.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Any x86-64 or ARM | ARMv8+ (Raspberry Pi 4+) |
| RAM | 256 MB | 512 MB+ |
| Storage | 100 MB | 1 GB+ |
| Network | Ethernet or WiFi | Ethernet |
| OS | Linux (any) | Raspberry Pi OS, Ubuntu |

Zend runs entirely on Python standard library — no Docker, no Node.js, no external dependencies.

## Step 1: Install Zend

### Option A: Clone the Repository

```bash
# Install Git if needed
sudo apt update && sudo apt install -y git

# Clone the repo
git clone <repo-url> ~/zend
cd ~/zend
```

### Option B: Download and Extract

```bash
# Download the latest release
curl -L <release-url> -o zend.tar.gz
tar -xzf zend.tar.gz
cd zend
```

## Step 2: Configure Environment

Create a configuration file or set environment variables. Create `~/.zend-env`:

```bash
# ~/.zend-env - Source this before running Zend

# Where state files live
export ZEND_STATE_DIR="$HOME/zend-state"

# Bind to all interfaces (for LAN access)
# Use 0.0.0.0 for LAN, 127.0.0.1 for local-only
export ZEND_BIND_HOST="0.0.0.0"

# Daemon port
export ZEND_BIND_PORT="8080"

# How long pairing tokens are valid (hours)
export ZEND_TOKEN_TTL_HOURS="720"
```

Apply the configuration:

```bash
source ~/.zend-env
```

## Step 3: First Boot

Start the daemon and create your principal identity:

```bash
# Source your config
source ~/.zend-env

# Bootstrap (starts daemon + creates identity)
./scripts/bootstrap_home_miner.sh
```

**Expected output:**
```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
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

## Step 4: Find Your IP Address

```bash
# On the daemon machine
hostname -I
# Example: 192.168.1.100
```

Make note of this IP. You'll use it to connect from other devices.

## Step 5: Access the Command Center

From your phone or tablet (on the same network):

1. Open your browser
2. Navigate to `http://<daemon-ip>:8080/gateway`

   Replace `<daemon-ip>` with the IP from Step 4. Example:
   ```
   http://192.168.1.100:8080/gateway
   ```

3. You should see the Zend Home command center

If you see "Unable to connect", check the firewall settings below.

## Step 6: Pair Your Phone with Control Access

By default, bootstrap only grants `observe` capability. To control mining:

```bash
# On the daemon machine
source ~/.zend-env
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

**Expected output:**
```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00Z"
}

paired my-phone
capability=observe,control
```

## Daily Operations

### Check Status

```bash
# CLI on daemon machine
source ~/.zend-env
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Or from your phone's browser at `http://<daemon-ip>:8080/gateway`.

### Start Mining

```bash
source ~/.zend-env
./scripts/set_mining_mode.sh --client my-phone --mode balanced
# Or use the Start button in the web UI
```

### Stop Mining

```bash
source ~/.zend-env
./scripts/set_mining_mode.sh --client my-phone --mode paused
# Or use the Stop button in the web UI
```

### View Event Log

```bash
source ~/.zend-env
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20
```

## Recovery

### Daemon Won't Start

**Symptom:** Bootstrap fails with "Daemon failed to start"

```bash
# Check if port is in use
lsof -i :8080

# Kill existing process
pkill -f daemon.py

# Or use the stop script
./scripts/bootstrap_home_miner.sh --stop

# Try again
./scripts/bootstrap_home_miner.sh
```

### State is Corrupted

**Symptom:** CLI returns errors about principal or pairing

```bash
# Backup existing state
mv state state.bak

# Re-bootstrap (creates fresh identity)
./scripts/bootstrap_home_miner.sh
```

### Forgot Device Capabilities

```bash
# List all paired devices
cat state/pairing-store.json

# Check specific device
python3 -c "import json; data=json.load(open('state/pairing-store.json')); print(json.dumps(data, indent=2))"
```

### Phone Can't Connect

1. **Verify daemon is running:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **Check firewall on daemon machine:**
   ```bash
   # Allow port 8080
   sudo ufw allow 8080/tcp
   ```

3. **Verify network connectivity:**
   ```bash
   # From phone, test connection
   ping <daemon-ip>
   
   # Or in browser dev tools, check for CORS errors
   ```

## Security Considerations

### LAN-Only by Default

Zend is designed to run on your local network. The daemon binds to `0.0.0.0` (all interfaces) but **only accepts connections from your LAN**.

### Don't Expose to Internet

- **Do NOT** port-forward port 8080 to the internet
- **Do NOT** bind to a public IP address
- **Do NOT** disable the pairing requirement

### If You Need Remote Access

For now, use a VPN (Tailscale, WireGuard) to access your LAN remotely. Future versions may include secure remote access built-in.

### Revoking Access

To revoke a paired device:

```bash
# Remove pairing from store
python3 -c "
import json
data = json.load(open('state/pairing-store.json'))
# Remove unwanted devices
del data['<device-id>']
json.dump(data, open('state/pairing-store.json', 'w'), indent=2)
"
```

## Service Management

### Run as Systemd Service

Create `/etc/systemd/system/zend.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
EnvironmentFile=/home/pi/.zend-env
ExecStart=/usr/bin/python3 /home/pi/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend.service
sudo systemctl start zend.service

# Check status
sudo systemctl status zend.service

# View logs
journalctl -u zend.service -f
```

## Troubleshooting Matrix

| Problem | Cause | Solution |
|---------|-------|----------|
| Can't connect from phone | Firewall blocking | `sudo ufw allow 8080/tcp` |
| Daemon won't start | Port in use | `pkill -f daemon.py; ./scripts/bootstrap_home_miner.sh` |
| "Device already paired" | Duplicate pairing | Use different device name |
| UI shows "offline" | Daemon not running | `./scripts/bootstrap_home_miner.sh` |
| "unauthorized" error | Lacks capability | Re-pair with `--capabilities observe,control` |
| Event log empty | New installation | Normal for fresh install; events appear on actions |

## Next Steps

- Read [API Reference](api-reference.md) for programmatic control
- Read [Architecture](architecture.md) to understand the system
- Review [DESIGN.md](../DESIGN.md) for the design system
