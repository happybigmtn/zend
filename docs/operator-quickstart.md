# Operator Quickstart — Zend on Home Hardware

This guide walks an operator through deploying Zend on a home Linux machine
(Raspberry Pi, mini PC, NAS, etc.). By the end you will have the daemon
running, a phone paired, and the command center accessible from the browser.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Any Linux-capable ARM or x86 | ARMv8+ or modern x86 |
| RAM | 256 MB | 512 MB |
| Storage | 100 MB | 1 GB |
| OS | Linux (Raspbian, Debian, Ubuntu) | Raspberry Pi OS or Ubuntu Server |
| Network | Wired or Wi-Fi LAN | Wired ethernet |

Zend runs entirely on the Python standard library. No Docker, no database
server, no Node.js needed.

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 2. Verify Python

```bash
python3 --version   # requires 3.10 or higher
```

On Raspberry Pi OS (Debian-based):

```bash
sudo apt update && sudo apt install -y python3 python3-venv
```

### 3. Set environment variables

For a LAN-accessible deployment, bind to your LAN interface instead of
localhost. Find your LAN IP:

```bash
hostname -I | awk '{print $1}'
# e.g. 192.168.1.100
```

Set the environment before every daemon start:

```bash
export ZEND_BIND_HOST=192.168.1.100
export ZEND_BIND_PORT=8080
export ZEND_STATE_DIR=/opt/zend/state
```

To make these permanent, add them to `/etc/environment` or a startup script:

```bash
echo 'export ZEND_BIND_HOST=192.168.1.100' | sudo tee -a /etc/profile.d/zend.sh
echo 'export ZEND_BIND_PORT=8080' | sudo tee -a /etc/profile.d/zend.sh
echo 'export ZEND_STATE_DIR=/opt/zend/state' | sudo tee -a /etc/profile.d/zend.sh
```

---

## First Boot

### 1. Start the daemon

```bash
cd /opt/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  ...
}
[INFO] Bootstrap complete
```

Save the `principal_id` and `pairing_id` from the output. You will need them
for device recovery.

### 2. Verify the daemon is running

```bash
curl http://192.168.1.100:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 12}
```

### 3. Verify the daemon is LAN-only

The daemon must not be reachable from the internet. Check:

```bash
# Should show only the LAN interface
ss -tlnp | grep 8080
```

The bind address should be your LAN IP, not `0.0.0.0` (unless you intentionally
want all interfaces).

---

## Pairing a Phone

### On the daemon machine

Grant `control` capability so the phone can change miner modes:

```bash
cd /opt/zend
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-23T..."
}
```

### On the phone

1. Open a browser on the phone.
2. Navigate to `http://192.168.1.100:8080/status` — you should see miner JSON.
3. To use the command center UI, open the file
   `apps/zend-home-gateway/index.html` from a local clone, or serve it:

   ```bash
   cd /opt/zend
   python3 -m http.server 9000 --directory apps/zend-home-gateway
   ```
   Then open `http://192.168.1.100:9000` on the phone.

4. The command center polls `http://192.168.1.100:8080` automatically.
   The miner status should appear on the Home screen.

---

## Daily Operations

### Check miner status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Start / stop mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action stop
```

### Change mining mode

Three modes are supported: `paused`, `balanced`, `performance`.

```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced
```

Expected response:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

### View event history

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events \
  --client my-phone --kind control_receipt --limit 20
```

### Run the no-hashing audit

Confirms the phone is only a control plane and does no hashing:

```bash
./scripts/no_local_hashing_audit.sh --client my-phone
# exit 0 = clean
```

---

## Keeping the Daemon Running

### Using systemd (recommended)

Create a unit file:

```bash
sudo nano /etc/systemd/system/zend.service
```

```
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend/state"
ExecStart=/usr/bin/python3 /opt/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend
sudo systemctl start zend

# Check status
sudo systemctl status zend
```

The daemon now starts automatically on boot.

### Check logs

```bash
journalctl -u zend -f
```

---

## Recovery

### State is corrupted

If the daemon fails to start or pairings are broken:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state (this deletes pairing records — you will need to re-pair devices)
rm -rf /opt/zend/state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

### Daemon won't start (port in use)

Another process is using port 8080. Find and stop it:

```bash
# Find the process
sudo lsof -i :8080

# Kill it
sudo kill <PID>
```

Then restart the daemon.

### Daemon crashes immediately

Check for missing Python:

```bash
python3 --version   # must be 3.10+
```

Run the daemon directly to see the error:

```bash
cd /opt/zend/services/home-miner-daemon
python3 daemon.py
```

### Need to re-pair a device

Pairing records live in `state/pairing-store.json`. To revoke a device:

```bash
# Remove the pairing
cd /opt/zend
python3 -c "
import json
store = json.load(open('state/pairing-store.json'))
# List all devices
for id_, p in store.items():
    print(id_, p['device_name'], p['capabilities'])
"

# Edit the file to remove the device, or:
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

---

## Security

### LAN-only is the default

The daemon binds to the address in `ZEND_BIND_HOST`. It never opens a public
port.

**Do not** set `ZEND_BIND_HOST=0.0.0.0` on an internet-facing machine. The
daemon has no authentication layer in milestone 1 — it is designed for LAN use
only.

### Pairing tokens

Pairing tokens are valid for 24 hours by default (`ZEND_TOKEN_TTL_HOURS=24`).
Tokens are single-use — replaying an old token is rejected and logged as
`PAIRING_TOKEN_REPLAY`.

### What is not exposed

In milestone 1, the daemon does not:
- Require a password or API key
- Use TLS (LAN-only; upgrade path is documented in the architecture doc)
- Accept remote connections outside your LAN

### Firewall configuration (optional)

If you want to be extra cautious, restrict port 8080 to your LAN subnet:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8080
sudo ufw enable
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use LAN IP for remote access) |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `./state/` | State file directory |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Pairing token validity window |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI commands |

Set these in `/etc/environment` or a systemd unit `Environment=` line.
