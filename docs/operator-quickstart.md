# Operator Quickstart — Zend Home on Home Hardware

This guide walks an operator through deploying the Zend Home Miner daemon on
a Raspberry Pi or similar Linux box, pairing a phone, and running the system
day-to-day.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Any Linux-capable ARM or x86 | Raspberry Pi 4 (4 GB) or better |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB free | 8 GB SD card or SSD |
| OS | Raspberry Pi OS (64-bit) or Ubuntu 22.04+ | Same |
| Network | Ethernet or Wi-Fi on a LAN | Ethernet |
| Python | 3.10+ | 3.10 or 3.11 |

The daemon uses negligible CPU and RAM when idle. It is a control surface,
not a miner — it does not perform hashing work.

---

## Installation

### 1. Transfer the Repo

On your workstation:

```bash
git clone <repo-url> /path/to/zend
scp -r /path/to/zend operator@<pi-ip>:/home/operator/zend
```

Or clone directly on the Pi:

```bash
ssh operator@<pi-ip>
git clone <repo-url> ~/zend
cd ~/zend
```

### 2. Verify Python

```bash
python3 --version   # must be 3.10 or higher
```

If not, install it:

```bash
sudo apt update && sudo apt install -y python3 python3-venv
```

### 3. No pip Install

Zend uses only the Python standard library. No `pip install`, no virtual
environment, no external dependencies.

---

## Configuration

The daemon is controlled entirely by environment variables. Set these in your
shell or in a systemd service file.

| Variable | Default | What to change it to |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | `0.0.0.0` for LAN access |
| `ZEND_BIND_PORT` | `8080` | Any unused port |
| `ZEND_STATE_DIR` | `./state` | A persistent path, e.g. `/home/operator/zend/state` |

### Recommended Production Settings

```bash
export ZEND_BIND_HOST=0.0.0.0        # Listen on all LAN interfaces
export ZEND_BIND_PORT=8080            # Default port
export ZEND_STATE_DIR=/home/operator/zend/state
```

> **Security note:** The daemon is intentionally LAN-only for milestone 1.
> Do not bind to a public interface or forward port 8080 to the internet.
> The daemon has no authentication layer — it relies on network-level
> isolation. Only run it on a trusted LAN.

---

## First Boot

### 1. Bootstrap

```bash
cd ~/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 0.0.0.0:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1234)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T00:00:00+00:00"
}
[INFO] Bootstrap complete
```

The `principal_id` and `pairing_id` are written to `state/`. The pairing for
`alice-phone` is created with `observe` capability.

### 2. Verify Health

```bash
curl http://localhost:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### 3. Upgrade to Control Capability (optional)

The default `alice-phone` pairing has `observe` only. To allow starting and
stopping mining:

```bash
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 cli.py pair --device alice-phone --capabilities observe,control
```

### 4. Check Status

```bash
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 cli.py status --client alice-phone
```

Expected:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T00:00:00+00:00"
}
```

---

## Pairing a Phone

The command center UI is a single HTML file that runs in any browser. To pair
and access it from your phone:

### 1. Serve the UI Over LAN

On the Pi, serve the HTML file:

```bash
cd ~/zend
python3 -m http.server 3000 --bind 0.0.0.0 &
```

Or use systemd to keep it running (see the systemd section below).

### 2. Access from Phone

Open your phone's browser and navigate to:

```
http://<pi-ip>:3000/apps/zend-home-gateway/index.html
```

The UI connects to `http://<pi-ip>:8080` for miner data.

### 3. Pair via CLI (First Pairing Already Done)

If you need to pair a second phone:

```bash
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 cli.py pair --device bob-phone --capabilities observe,control
```

Pairing creates a record in `state/pairing-store.json`. The phone does not
need to be on the same machine — the pairing token is written to the store
on the daemon side.

---

## Opening the Command Center

After pairing, the HTML UI at `http://<pi-ip>:3000/apps/zend-home-gateway/index.html`
shows:

- **Status Hero** — miner state (Running / Stopped / Offline), mode, hashrate, temperature
- **Mode Switcher** — Paused / Balanced / Performance segmented control
- **Quick Actions** — Start Mining / Stop Mining buttons
- **Latest Receipt** — most recent control action receipt
- **Bottom Nav** — Home, Inbox, Agent, Device tabs

The UI polls `/status` every 5 seconds. If the daemon is unreachable, a banner
appears: "Unable to connect to Zend Home".

---

## Daily Operations

### Check Miner Status

```bash
curl http://localhost:8080/status
```

### Start Mining

```bash
curl -X POST http://localhost:8080/miner/start
# {"success": true, "status": "running"}
```

Or via CLI:

```bash
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 cli.py control --client alice-phone --action start
```

### Stop Mining

```bash
curl -X POST http://localhost:8080/miner/stop
```

### Change Mining Mode

```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
# {"success": true, "mode": "balanced"}
```

### View Event Spine

```bash
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 cli.py events --client alice-phone --kind all --limit 10
```

### Stop the Daemon

```bash
kill $(cat ~/zend/state/daemon.pid)
```

---

## Recovery

### Daemon Won't Start

1. Check if the port is already in use:

   ```bash
   lsof -i :8080
   ```

2. Kill any existing process, then retry:

   ```bash
   kill <PID>
   ./scripts/bootstrap_home_miner.sh
   ```

### State Is Corrupted

State is safe to delete — it is reconstructable from bootstrap:

```bash
cd ~/zend
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

This creates a new `principal_id` and a fresh pairing for `alice-phone`.

### Bootstrap Fails With "Daemon failed to start"

Check that `ZEND_BIND_HOST` and `ZEND_BIND_PORT` are not already in use.
Try a different port:

```bash
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

### Phone Can't Reach the Daemon

1. Verify the daemon is listening on the right interface:

   ```bash
   ss -tlnp | grep 8080
   # Should show 0.0.0.0:8080 or :::8080
   ```

2. Verify the phone is on the same LAN subnet.

3. Check the Pi firewall:

   ```bash
   sudo iptables -L -n   # look for DROP rules on port 8080
   sudo ufw allow 8080/tcp
   ```

4. From the phone, test connectivity:

   ```bash
   # On the phone's browser, navigate to:
   http://<pi-ip>:8080/health
   ```

### Pairing Rejected — "Device already paired"

```bash
# Remove the existing pairing and re-pair
cd ~/zend/services/home-miner-daemon
ZEND_STATE_DIR=/home/operator/zend/state \
  python3 -c "
import json, sys
sys.path.insert(0, '.')
from store import load_pairings, save_pairings
p = load_pairings()
# Find and remove the device
for k, v in list(p.items()):
    if v['device_name'] == 'alice-phone':
        del p[k]
save_pairings(p)
print('Removed alice-phone pairing')
"
# Then re-bootstrap
cd ~/zend && ./scripts/bootstrap_home_miner.sh
```

---

## Running as a systemd Service

For a persistent daemon that starts on boot:

Create `/etc/systemd/system/zend-home.service`:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=operator
WorkingDirectory=/home/operator/zend
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/home/operator/zend/state"
ExecStart=/usr/bin/python3 /home/operator/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zend-home
sudo systemctl status zend-home
```

Stop and start:

```bash
sudo systemctl stop zend-home
sudo systemctl start zend-home
```

View logs:

```bash
sudo journalctl -u zend-home -f
```

---

## Security Notes

- **LAN-only by design.** The daemon binds to `0.0.0.0` on the LAN, not the
  internet. Do not port-forward 8080 from your router.
- **No auth on the HTTP interface.** Access is controlled by network isolation.
  Only trusted devices on your LAN should be able to reach port 8080.
- **Pairing is device-level.** There is no per-user auth. Anyone with a paired
  device name can issue commands up to that device's capability level.
- **State files contain secrets.** `state/principal.json` and
  `state/pairing-store.json` should be readable only by the operator account.
  The `state/` directory is gitignored — back it up if you want to preserve
  your principal identity across reinstalls.
- **The event spine is append-only.** Events written to `state/event-spine.jsonl`
  are never deleted. This is intentional for audit purposes.
