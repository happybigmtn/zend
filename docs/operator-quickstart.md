# Operator Quickstart

This guide deploys the Zend Home Miner daemon on a Linux machine — a Raspberry Pi,
a spare desktop, a NAS, or any home hardware. It assumes no programming knowledge
and no pip install. The system is designed to run headless and be controlled from
a phone or tablet on the same network.

## Hardware Requirements

- Any Linux system (Raspberry Pi OS, Ubuntu, Debian)
- Python 3.10 or later
- 100 MB disk space
- Ethernet or Wi-Fi on your LAN

Verify Python is available:

```bash
python3 --version   # expects Python 3.10 or later
```

If Python is not installed:

```bash
# Raspberry Pi OS / Debian / Ubuntu
sudo apt update && sudo apt install -y python3 python3-venv
```

## Installation

There is no pip install and no build step.

```bash
# Clone the repository
git clone <repo-url> && cd zend

# Verify the bootstrap script is present
ls scripts/bootstrap_home_miner.sh   # should print the file path
```

## Configuration

The daemon respects four environment variables. The defaults work for first boot.

| Variable           | Default       | Description                              |
| ------------------ | ------------- | ---------------------------------------- |
| `ZEND_STATE_DIR`   | `./state`     | Where pairing and principal data lives   |
| `ZEND_BIND_HOST`   | `127.0.0.1`   | **Change to `0.0.0.0` for LAN access**   |
| `ZEND_BIND_PORT`   | `8080`        | TCP port for the daemon                  |
| `ZEND_TOKEN_TTL_HOURS` | `8760`    | Pairing token lifetime (1 year default)   |

For LAN access (control from your phone on the same network):

```bash
export ZEND_BIND_HOST=0.0.0.0
export ZEND_BIND_PORT=8080
```

Add these to your shell profile to persist across reboots:

```bash
echo 'export ZEND_BIND_HOST=0.0.0.0' >> ~/.bashrc
echo 'export ZEND_BIND_PORT=8080' >> ~/.bashrc
```

## First Boot

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-..."
}
[INFO] Bootstrap complete
```

Save the `principal_id` — it is your home's unique identity. The `pairing_id`
is the credential for the default device.

The daemon is now running in the background. Take note of the PID from the
`state/daemon.pid` file.

### Verify the Daemon Is Running

```bash
curl http://127.0.0.1:8080/health
```

Expected:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 12}
```

## Pairing a Phone or Tablet

The bootstrap creates a pairing for `alice-phone` with `observe` capability only.
To grant control capability, pair a separate device (multiple devices can coexist):

```bash
# Pair a new device with both observe and control
python3 services/home-miner-daemon/cli.py pair \
  --device "my-phone" \
  --capabilities "observe,control"
```

Valid capabilities: `observe` (read-only), `control` (can change miner state).

## Opening the Command Center

The command center is a single HTML file. To access it from your phone:

1. Open the file `apps/zend-home-gateway/index.html` in your phone's browser.

For a phone to reach the daemon over LAN, the daemon must be bound to `0.0.0.0`:

```bash
ZEND_BIND_HOST=0.0.0.0 ./scripts/bootstrap_home_miner.sh
```

Then find your machine's LAN IP:

```bash
hostname -I | awk '{print $1}'
```

Access the command center from the phone:

```
http://<your-machine-ip>:8080/
```

Or copy `apps/zend-home-gateway/index.html` to the phone and open it locally.
The HTML polls `http://127.0.0.1:8080` by default — edit the `API_BASE` constant
near line 1 of the `<script>` block to point to your machine's IP if needed.

## Daily Operations

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Change Mining Mode

```bash
# Pause mining
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode paused

# Balanced mode (moderate hashrate, moderate heat)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced

# Performance mode (maximum hashrate, more heat)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode performance
```

### Start and Stop Mining

```bash
# Start
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action stop
```

### View Operational Events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 20
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Restart the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Check Daemon Status Without Starting It

```bash
./scripts/bootstrap_home_miner.sh --status
```

## Recovery

### Daemon Won't Start — Port Already in Use

```bash
# Find and kill the process on port 8080
fuser -k 8080/tcp

# Restart
./scripts/bootstrap_home_miner.sh
```

### State Is Corrupt or Unknown

State files live in `state/`. They are safe to delete at any time.

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Re-bootstrap from scratch
./scripts/bootstrap_home_miner.sh
```

This creates a fresh `PrincipalId` and a fresh pairing for `alice-phone`.

### Pairing Is Lost

If the phone loses its pairing record, wipe the pairing store and re-pair:

```bash
# Remove all pairings (or manually edit state/pairing-store.json to remove one)
rm state/pairing-store.json

# Re-pair the device
python3 services/home-miner-daemon/cli.py pair \
  --device "my-phone" \
  --capabilities "observe,control"
```

## Security Notes

**LAN-only by design.** The daemon binds to `127.0.0.1` by default. Binding to
`0.0.0.0` exposes it on your local network only — not the internet. Do not
forward port 8080 to the internet.

**No authentication on the daemon itself.** Pairing records and capability grants
are the access control. If your LAN is untrusted, run the daemon on a VLAN or
VPN segment.

**No encryption of daemon traffic in milestone 1.** The LAN assumption means the
control surface is considered trusted within the home network. TLS is a future
milestone.

**Pairing tokens are long-lived.** Default TTL is 8760 hours (1 year). Revoke
old pairings by wiping `state/pairing-store.json` and re-pairing.

## Headless Deployment

To run the daemon as a persistent service (systemd):

```bash
sudo tee /etc/systemd/system/zend-home-miner.service << 'EOF'
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/path/to/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=0.0.0.0"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/path/to/zend/state"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-home-miner
sudo systemctl start zend-home-miner
sudo systemctl status zend-home-miner
```

## State File Reference

| File                  | Contents                                      |
| --------------------- | --------------------------------------------- |
| `state/principal.json` | Your home's `PrincipalId`                     |
| `state/pairing-store.json` | All paired devices and their capabilities |
| `state/event-spine.jsonl` | Append-only log of all events           |
| `state/daemon.pid`    | PID of the running daemon                     |
