# Operator Quickstart — Home Hardware Deployment

This guide covers deploying Zend Home Miner on a Raspberry Pi or similar home hardware. No cloud, no internet-facing ports, no external dependencies.

## What You Need

- Raspberry Pi 4 (or equivalent ARM64 board) running Raspberry Pi OS or Ubuntu Server
- Python 3.10+ pre-installed
- Home network (Wi-Fi or Ethernet)
- A phone or tablet to run the command center

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│  Your Phone / Tablet (browser)                      │
│  apps/zend-home-gateway/index.html                  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (LAN)
                   ▼
┌─────────────────────────────────────────────────────┐
│  Raspberry Pi — Zend Home Miner Daemon              │
│  services/home-miner-daemon/                        │
│  Binds to: <pi-ip>:8080                             │
│  State: /home/pi/zend/state/                         │
└─────────────────────────────────────────────────────┘
                   │
                   ▼
         Your Mining Hardware
         (real miner or MinerSimulator)
```

Zend is **LAN-only**. The daemon never connects to the internet and does not require port forwarding.

## Step 1 — Set Up the Hardware

### Install Python 3

```bash
# Raspberry Pi OS
sudo apt update && sudo apt install -y python3 python3-pip

# Verify
python3 --version  # Should be 3.10+
```

### Clone the Repository

```bash
# On the Pi
git clone <repo-url> ~/zend
cd ~/zend
```

### Find Your Pi's LAN IP

```bash
hostname -I | awk '{print $1}'
# Example output: 192.168.1.50
```

You'll use this IP for the `ZEND_BIND_HOST` environment variable.

## Step 2 — Configure the Daemon

Create a systemd service so the daemon starts automatically:

```bash
sudo nano /etc/systemd/system/zend-home.service
```

Paste the following (replace `/home/pi/zend` with your actual clone path and `192.168.1.50` with your Pi's IP):

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/usr/bin/python3 /home/pi/zend/services/home-miner-daemon/daemon.py
Environment="ZEND_BIND_HOST=192.168.1.50"
Environment="ZEND_BIND_PORT=8080"
Environment="ZEND_STATE_DIR=/home/pi/zend/state"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home

# Check it's running
sudo systemctl status zend-home
```

## Step 3 — Bootstrap the Principal Identity

SSH into the Pi or open a terminal:

```bash
cd ~/zend
./scripts/bootstrap_home_miner.sh
```

Expected output:

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
```

Save the `principal_id`. You'll use it to pair additional devices.

## Step 4 — Open the Command Center

On your phone or tablet, open the browser and navigate to:

```
file:///home/pi/zend/apps/zend-home-gateway/index.html
```

> **Note:** For the browser to load a `file://` URL that fetches from an HTTP server, the daemon must be running and reachable. For easier mobile access, consider serving the HTML over HTTP:
>
> ```bash
> # On the Pi, serve the gateway as a simple static file server
> cd ~/zend
> python3 -m http.server 3000 --directory apps/zend-home-gateway
> ```
>
> Then on your phone, open: `http://192.168.1.50:3000`

The page polls the daemon every 5 seconds and shows:
- Current miner status (running / stopped)
- Mining mode (paused / balanced / performance)
- Hashrate
- Latest control receipt

## Step 5 — Pair Additional Devices

From the Pi's terminal:

```bash
# Pair a second device with observe + control
python3 services/home-miner-daemon/cli.py pair \
    --device my-phone \
    --capabilities observe,control

# List paired devices
python3 services/home-miner-daemon/cli.py events --kind pairing_granted --limit 10
```

## Controlling the Miner Remotely

From any machine on your LAN that has the repo cloned:

```bash
export ZEND_DAEMON_URL=http://192.168.1.50:8080

# Check health
python3 services/home-miner-daemon/cli.py health

# Start mining
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone \
    --action start

# Set mode
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone \
    --action set_mode \
    --mode balanced
```

## Monitoring

```bash
# Watch live status
watch python3 services/home-miner-daemon/cli.py status

# Tail the event spine
tail -f state/event-spine.jsonl | python3 -m json.tool --no-ensure-ascii

# Check daemon logs (systemd)
sudo journalctl -u zend-home -f
```

## Updating

```bash
# On the Pi
cd ~/zend
git pull

# Restart the service
sudo systemctl restart zend-home
```

## Security Notes

- **Never bind to `0.0.0.0`**. Always use the Pi's specific LAN IP.
- **No authentication for milestone 1**. Capability is enforced by device name lookup only. Do not expose the daemon port beyond your LAN.
- **No hashing on the control device**. The phone/tablet is a thin client — all mining compute happens on the Pi or your dedicated mining hardware.
- Run the daemon under a limited user account, not root. The provided systemd unit uses `User=pi`.

## Troubleshooting

### Daemon won't start

```bash
sudo journalctl -u zend-home -e
```

Common causes:
- Port 8080 already in use: `lsof -i :8080`
- State directory missing: `mkdir -p ~/zend/state`

### Phone can't reach the daemon

1. Verify the Pi's firewall allows inbound on port 8080:
   ```bash
   sudo ufw allow 8080/tcp
   ```
2. Confirm the Pi's IP hasn't changed. Assign a static DHCP lease in your router.

### MinerSimulator vs. Real Miner

Milestone 1 ships with `MinerSimulator` — an in-memory mock that simulates miner state. To connect a real miner backend, replace the `MinerSimulator` instance in `daemon.py` with an HTTP client to your hardware's control API. The HTTP contract is the same.
