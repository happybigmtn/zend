# Operator Quickstart — Zend Home on Home Hardware

This guide walks you through deploying Zend Home on a Linux machine in your house. It covers hardware requirements, installation, configuration, first boot, pairing a phone, and daily operations.

By the end of this guide you will have:
- The Zend Home Miner Daemon running on your machine
- A phone paired as a control client
- The command center accessible from the phone's browser

---

## 1. Hardware Requirements

| Component | Requirement |
|---|---|
| CPU | Any x86-64 or ARM processor (Raspberry Pi 3B+ or newer works) |
| Memory | 256 MB RAM minimum |
| Disk | 50 MB free space |
| OS | Linux (Ubuntu 20.04+, Raspberry Pi OS, Debian 11+) |
| Network | Ethernet or Wi-Fi; the machine must be on the same LAN as your phone |
| Python | Python 3.10 or newer (`python3 --version`) |

The daemon is lightweight. A Raspberry Pi is sufficient.

---

## 2. Installation

### Clone the Repository

```bash
git clone <repo-url> /opt/zend-home
cd /opt/zend-home
```

No `pip install`, no build step. Python 3.10+ is the only requirement.

Verify Python:

```bash
python3 --version
# Must be Python 3.10 or newer
```

### Directory Layout

```
/opt/zend-home/
  services/home-miner-daemon/
  apps/zend-home-gateway/
  scripts/
  state/          ← created at first boot, stores pairing and events
```

The `state/` directory is created automatically and is gitignored. It is safe to leave in the repo clone.

---

## 3. Configuration

Set these environment variables before starting the daemon.

### Configuration File (Recommended)

Create `/opt/zend-home/.env` with your settings:

```bash
# Bind to LAN interface (not 0.0.0.0 for full internet exposure — see §9 Security)
ZEND_BIND_HOST=192.168.1.100   # ← your machine's LAN IP
ZEND_BIND_PORT=8080
ZEND_STATE_DIR=/opt/zend-home/state
```

Replace `192.168.1.100` with your machine's LAN IP address. Find it with:

```bash
ip addr show | grep "inet "     # Linux
hostname -I                       # Linux, simpler
```

### Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | LAN IP address of this machine |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `./state` | Where pairing, principal, and event files are stored |
| `ZEND_TOKEN_TTL_HOURS` | (none) | Pairing token TTL in hours (not enforced in milestone 1) |

---

## 4. First Boot

### Start the Daemon

```bash
cd /opt/zend-home
source .env
python3 services/home-miner-daemon/daemon.py &
```

Or use the bootstrap script, which starts the daemon and creates your principal identity:

```bash
cd /opt/zend-home
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
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

### Verify the Daemon Is Running

```bash
curl http://192.168.1.100:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Start on Boot (systemd)

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/zend-home
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/opt/zend-home/state"
ExecStart=/usr/bin/python3 /opt/zend-home/services/home-miner-daemon/daemon.py
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
sudo systemctl status zend-home
```

---

## 5. Pairing a Phone

From your development machine (or the same machine the daemon runs on):

```bash
cd /opt/zend-home
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Or with Python directly:

```bash
cd services/home-miner-daemon/
python3 cli.py pair --device my-phone --capabilities observe,control
```

Expected output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:05:00+00:00"
}
```

**Pairing flow summary:**
1. A `PrincipalId` is created (one per installation)
2. A pairing record is created for the device name
3. `pairing_requested` and `pairing_granted` events are appended to the event spine
4. The device receives `observe` and/or `control` capability

---

## 6. Opening the Command Center

The daemon does not serve HTML. The command center is a single HTML file.

### Option A: Copy to the phone

Transfer `apps/zend-home-gateway/index.html` to your phone and open it in any browser. The page connects to the daemon at `http://192.168.1.100:8080`.

### Option B: Serve it locally

On the daemon machine:

```bash
cd /opt/zend-home
python3 -m http.server 8081 --directory apps/zend-home-gateway/
```

Then open `http://192.168.1.100:8081/` from your phone's browser.

### Option C: Open directly from the file system

Email or AirDrop `index.html` to yourself and open it from the Files app.

---

## 7. Daily Operations

### Check Daemon Health

```bash
curl http://192.168.1.100:8080/health
```

Or with the CLI:

```bash
python3 services/home-miner-daemon/cli.py health
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode paused

# Balanced mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced

# Performance mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode performance
```

### Start / Stop Mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action stop
```

### View Operational Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Only control receipts
python3 services/home-miner-daemon/cli.py events \
  --client my-phone --kind control_receipt --limit 10
```

### List Paired Devices

```bash
python3 services/home-miner-daemon/cli.py devices
```

---

## 8. Recovery

### State Is Corrupt

The state files are human-readable JSON and JSONL. If something is wrong:

```bash
# Stop the daemon first
sudo systemctl stop zend-home

# Backup the state
cp -r /opt/zend-home/state /opt/zend-home/state.bak

# Reset state
rm -rf /opt/zend-home/state
mkdir /opt/zend-home/state

# Restart
sudo systemctl start zend-home

# Re-pair devices
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Daemon Won't Start

Common causes:

**Port already in use:**
```bash
# Find what's using port 8080
sudo lsof -i :8080
# Kill it or change ZEND_BIND_PORT
```

**Python version too old:**
```bash
python3 --version   # Must be 3.10+
```

**State directory permissions:**
```bash
ls -la /opt/zend-home/state
# Should be owned by the user running the daemon
sudo chown -R $USER /opt/zend-home/state
```

### Device Lost or Replaced

To revoke a paired device:

```bash
# Manually edit state/pairing-store.json
# Remove the entry for the lost device
# Restart the daemon
sudo systemctl restart zend-home
```

The device will be unable to connect until it is re-paired.

### Restart After a Crash

If the daemon crashed (not stopped cleanly):

```bash
sudo systemctl restart zend-home
```

The state is preserved. Pairing records and event history survive restarts.

---

## 9. Security

### LAN-Only by Default

The daemon binds to `127.0.0.1` in development and to a specific LAN IP in production. It does **not** bind to `0.0.0.0` in milestone 1. Do not change `ZEND_BIND_HOST` to a public IP or `0.0.0.0`.

### What to Check

```bash
# Verify the daemon is listening on the expected interface only
ss -tlnp | grep 8080

# Expected: shows the LAN IP, not 0.0.0.0
# tcp LISTEN 192.168.1.100:8080 ...
```

### What Not to Expose

- The daemon control HTTP port (8080) should not be port-forwarded on your router
- The `state/` directory contains principal identities; treat it as sensitive
- Pairing tokens are currently not encrypted at rest (milestone 1 limitation)

### Future: Remote Access

Secure remote access (beyond LAN) is not in milestone 1. If you need access from outside your home network, use a VPN (e.g., WireGuard) to reach your LAN rather than exposing the daemon directly.

---

## 10. Troubleshooting

### "Unable to connect to Zend Home" in the browser

1. Check the daemon is running: `curl http://192.168.1.100:8080/health`
2. Check the phone is on the same Wi-Fi/LAN network
3. Check no firewall is blocking the daemon port: `sudo ufw status`
4. Verify the LAN IP in the HTML file's `API_BASE` constant matches your machine's IP

### "unauthorized" when reading status

The client device is not paired. Run `pair_gateway_client.sh` first.

### "unauthorized" when controlling

The client device has `observe` capability only. Pair with `observe,control` to control the miner:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Mode change has no effect

The MinerSimulator runs in-process. Verify with:

```bash
curl http://192.168.1.100:8080/status
```

### Event list is empty

Events are appended to `state/event-spine.jsonl`. Check the file exists:

```bash
cat /opt/zend-home/state/event-spine.jsonl
```
