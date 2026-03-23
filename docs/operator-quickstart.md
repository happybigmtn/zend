# Operator Quickstart

Deploy the Zend Home Miner daemon on a Raspberry Pi or any home Linux box. By
the end of this guide you will have the daemon running, a phone paired, and a
working CLI-based operating path on the home hardware. Phone-browser command
center access remains a follow-on slice, not a verified outcome here.

This guide assumes you are on the target machine (the one that will run the
daemon) and have a phone or second device on the same LAN.

## Hardware Requirements

- Any Linux machine: Raspberry Pi 3B+ or newer, old laptop, mini PC, NAS, etc.
- Python 3.10 or newer (`python3 --version`)
- LAN connectivity (Wi-Fi or Ethernet)
- Internet access for the initial clone

No GPU, no special mining hardware, no database server.

## Installation

### 1. Clone the Repository

On the target machine:

```
git clone <repo-url> ~/zend
cd ~/zend
```

### 2. Verify Python Version

```
python3 --version   # must be 3.10 or higher
```

If too old, install Python 3.10+:

```
# Debian/Ubuntu/Raspberry Pi OS
sudo apt update && sudo apt install -y python3 python3-venv
```

### 3. Choose a Bind Address

The daemon must listen on a LAN interface, not just localhost.

Find your LAN IP:

```
hostname -I
```

Example output: `192.168.1.100`

Set the bind address:

```
export ZEND_BIND_HOST=192.168.1.100
export ZEND_BIND_PORT=8080
```

To make this permanent, add to `~/.bashrc` or create a systemd unit (see
**Running as a Service** below).

## First Boot

### 1. Bootstrap the Daemon

```
cd ~/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 1234)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "..."
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. The PID is saved to `state/daemon.pid`.

### 2. Verify the Daemon is Up

From the same machine:

```
curl http://localhost:8080/health
```

Expected:

```
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

From the phone (replace `192.168.1.100` with your actual IP):

```
curl http://192.168.1.100:8080/health
```

Expected: same JSON response.

### 3. Command Center Status

The daemon does **not** serve the HTML command center in the current slice.
`http://192.168.1.100:8080` exposes only the JSON API (`/health`, `/status`,
`/miner/*`). The checked-in `apps/zend-home-gateway/index.html` is useful for
UI development, but opening it from a phone browser is currently blocked by the
combination of a hard-coded `127.0.0.1` API base and missing CORS headers on
the daemon.

For home-hardware operation today, use the CLI from the daemon machine for
status, pairing, and control. Treat phone-browser access as a follow-on slice,
not a verified part of this quickstart.

## Pairing a Phone

The bootstrap gave `alice-phone` observe-only access. To pair a real phone with
control capability:

### On the daemon machine:

```
cd ~/zend
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

Expected output:

```
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "..."
}
```

### On the phone:

Phone-browser UI access is not yet a verified deployment path. The paired
device name is recorded in `state/pairing-store.json` and will be used by a
future served command center.

## Daily Operations

### Check Miner Status

```
./scripts/read_miner_status.sh --client my-phone
```

Output includes JSON plus key fields:

```
status=running
mode=balanced
freshness=2026-03-22T10:00:00+00:00
```

### Change Mining Mode

```
./scripts/set_mining_mode.sh --client my-phone --mode performance
```

```
./scripts/set_mining_mode.sh --client my-phone --action stop
```

```
./scripts/set_mining_mode.sh --client my-phone --action start
```

All commands print a JSON response plus `acknowledged=true` on success.

### View Recent Events

```
./scripts/read_miner_status.sh --client my-phone   # daemon health
python3 services/home-miner-daemon/cli.py events --client my-phone --limit 20
```

### View Event Spine Directly

```
cat state/event-spine.jsonl
```

Each line is a JSON event. Use `jq` to pretty-print:

```
cat state/event-spine.jsonl | jq .
```

### Stop and Restart the Daemon

```
# Stop
./scripts/bootstrap_home_miner.sh --stop

# Restart
./scripts/bootstrap_home_miner.sh
```

## Running as a Service (systemd)

For persistent operation across reboots:

### 1. Create a systemd unit file

```
sudo nano /etc/systemd/system/zend-home.service
```

Paste:

```
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>/zend
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/home/<your-username>/zend/state"
ExecStart=/usr/bin/python3 /home/<your-username>/zend/services/home-miner-daemon/daemon.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Replace `<your-username>` and `192.168.1.100` with your actual values.

### 2. Enable and start

```
sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home
```

### 3. Verify

```
systemctl status zend-home
curl http://192.168.1.100:8080/health
```

## Security

The daemon is LAN-only by design. Do not expose port 8080 to the internet
without a reverse proxy and TLS terminator in front of it. The milestone 1
daemon has no authentication; anyone on the LAN who can reach the port can issue
control commands.

Current security model for milestone 1:
- Only devices on the same LAN can reach the daemon
- Pairing records are stored locally in `state/pairing-store.json`
- `observe` capability: read status and health
- `control` capability: start/stop/set_mode
- No token expiry or revocation in milestone 1

For production use, add TLS and a shared secret or mTLS.

## Recovery

### State is Corrupted

```
cd ~/zend
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

This wipes and recreates all local state (principal identity, pairing records,
event spine). You will need to re-pair all clients.

### Daemon Won't Start (Port Already in Use)

```
sudo lsof -i :8080
# Kill the process holding the port, then:
./scripts/bootstrap_home_miner.sh
```

### Daemon Crashes Immediately

Run it directly to see error output:

```
cd ~/zend
python3 services/home-miner-daemon/daemon.py
```

Common causes: bad environment variable values, `state/` not writable, Python
version too old.

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Address the daemon listens on. Use LAN IP for home deployment. |
| `ZEND_BIND_PORT` | `8080` | Port the daemon listens on. |
| `ZEND_STATE_DIR` | `<repo>/state` | Directory for principal, pairing, and spine files. |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Base URL for CLI commands. Override when running CLI from a different host. |
| `ZEND_TOKEN_TTL_HOURS` | (not used in milestone 1) | Token expiry window. |

## Troubleshooting

### Phone can't reach the daemon

1. Confirm the phone is on the same LAN as the daemon machine.
2. Check the daemon is binding to the LAN interface, not just `127.0.0.1`:

   ```
   curl http://localhost:8080/health          # works?
   curl http://192.168.1.100:8080/health      # works from same machine?
   ```

   If the second command fails, the daemon is not bound to the LAN interface.
   Set `ZEND_BIND_HOST=192.168.1.100` and restart.

3. Check firewall rules on the daemon machine:

   ```
   # Linux (ufw)
   sudo ufw allow 8080/tcp
   ```

### HTML command center shows "Unable to connect"

This is expected in the current slice. The UI hard-codes
`http://127.0.0.1:8080`, which refers to the phone itself, and the daemon does
not emit CORS headers for cross-origin browser requests. Use the CLI on the
daemon machine for operations until the UI is served from the daemon.

### Bootstrap hangs waiting for daemon

The daemon takes a few seconds to start. If it hangs more than 10 seconds,
the daemon likely failed to bind the port. Check with:

```
sudo lsof -i :8080
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```
