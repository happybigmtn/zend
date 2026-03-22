# Operator Quickstart — Zend Home on Home Hardware

This guide walks an operator through setting up Zend Home on a Raspberry Pi,
mini PC, or NAS — any home machine that can run Python and stay on the local
network 24/7.

---

## What You Need

| Item | Recommended | Minimum |
|------|-------------|---------|
| Hardware | Raspberry Pi 4 (4 GB) or mini PC | Raspberry Pi 3B+ |
| OS | Raspberry Pi OS Lite (64-bit) or Debian | Any Linux with Python 3.10+ |
| Storage | 16 GB SD card or SSD | 8 GB |
| Network | Ethernet preferred; Wi-Fi works | Same LAN as your phone |
| Phone | iOS 16+ or Android 12+ | Any modern browser |

Zend Home is designed to run headless on a small, always-on machine. It does
not need a desktop environment or a monitor.

---

## Step 1 — Flash the OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Choose **Raspberry Pi OS Lite (64-bit)**.
3. Click the gear icon and set:
   - Hostname: `zend-home`
   - Enable SSH with password authentication
   - Set a strong pi password
   - Configure Wi-Fi (if not using Ethernet)
4. Write the image to the SD card.

---

## Step 2 — First Boot and SSH

1. Insert the SD card and power on the device.
2. Wait ~2 minutes for first boot.
3. SSH in:

```bash
ssh pi@zend-home.local
# password: the one you set in the Imager
```

4. Update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3 — Install Zend

From the home directory on the device:

```bash
# Install Python 3 if not present
sudo apt install -y python3 python3-pip git

# Clone the repository (use your fork or the canonical URL)
git clone https://github.com/your-org/zend.git
cd zend
```

For air-gapped or bandwidth-constrained environments, clone on a development
machine and copy to the device via SD card or USB drive:

```bash
# On your development machine:
git clone https://github.com/your-org/zend.git
tar --exclude='.git' -czf zend.tar.gz zend/

# Copy zend.tar.gz to the device by any means, then:
ssh pi@zend-home.local
cd ~
tar -xzf zend.tar.gz
cd zend
```

---

## Step 4 — Bootstrap the Daemon

Run the bootstrap script:

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
bootstrap started
pairing_token=eyJhbGci...
principal_id=550e8400-e29b-41d4-a716-446655440000
daemon listening on 192.168.1.50:8080  # your LAN IP
```

**Write down the pairing token.** You need it for the next step. If you lose it,
re-run bootstrap to get a new one.

---

## Step 5 — Pair Your Phone

### Option A — From a Browser on Your Phone

1. Open the pairing URL shown at the end of bootstrap, or navigate directly to
   `http://<device-lan-ip>:8080/pair?token=<your-token>`.
2. The trust ceremony screen appears. Read what `observe` and `control`
   permissions mean.
3. Name your device (e.g., "Alice's Phone").
4. Tap **Pair**. The device is now registered.

### Option B — From the CLI (Headless Pairing)

```bash
./scripts/pair_gateway_client.sh --client alice-phone
```

This pairs a device named `alice-phone` with `observe` and `control`
capability. For a read-only pairing, use:

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
```

---

## Step 6 — Access the Gateway Client

Open a browser and navigate to:

```
http://<device-lan-ip>:8080
```

You see the Zend Home command center with four tabs:

| Tab | What You'll See |
|-----|----------------|
| **Home** | Miner status, mode, hashrate, temperature, freshness |
| **Inbox** | Pairing approvals, control receipts, alerts, Hermes summaries |
| **Agent** | Hermes connection state and delegated authority |
| **Device** | Device name, permissions, pairing management |

The client polls for new status every 5 seconds.

---

## Step 7 — Control the Miner

From the Home tab, use the **Mode Switcher** or **Start / Stop** buttons.

From the CLI:

```bash
# Read current status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Stop mining
./scripts/set_mining_mode.sh --client alice-phone --action stop
```

Every control action appends a receipt to the encrypted operations inbox.

---

## Operating States and What They Mean

| Miner State | Meaning |
|-------------|---------|
| `running` | Actively hashing on the home machine |
| `stopped` | Mining is off; daemon is healthy |
| `offline` | Daemon cannot reach the miner backend |
| `error` | Daemon or miner hit an error condition |

| Mode | What It Does |
|------|-------------|
| `paused` | No mining work; lowest power and heat |
| `balanced` | Moderate hashrate; manageable heat and power |
| `performance` | Maximum hashrate; higher power and heat |

The Status Hero shows the current state with a color indicator:

- Green dot: running
- Grey dot: stopped
- Red dot: error or offline

---

## Keeping Zend Running After SSH

Use `systemd` to keep the daemon alive across reboots:

```bash
# Create the service file
sudo nano /etc/systemd/system/zend-home.service
```

Paste:

```ini
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/zend
ExecStart=/usr/bin/python3 /home/pi/zend/services/home-miner-daemon/daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable zend-home
sudo systemctl start zend-home
```

Check status:

```bash
sudo systemctl status zend-home
```

View logs:

```bash
journalctl -u zend-home -f
```

---

## Upgrading Zend

```bash
cd ~/zend
git pull origin main
sudo systemctl restart zend-home
```

If the upgrade changes the daemon API, re-run pairing:

```bash
./scripts/pair_gateway_client.sh --client alice-phone --force
```

---

## Resetting State

If the daemon state becomes corrupt or you want a clean start:

```bash
# Stop the daemon
sudo systemctl stop zend-home

# Wipe state
rm -rf ~/zend/state/*

# Restart
sudo systemctl start zend-home

# Re-pair
./scripts/pair_gateway_client.sh --client alice-phone
```

---

## Network Access (Beyond LAN)

Remote access is explicitly **not in scope for milestone 1**. The daemon binds
LAN-only for a reason: it keeps the blast radius of any security incident to your
home network.

If you need remote access in a later milestone, the architecture is designed to
support it via a secure tunnel (see `TODOS.md` — P1: Secure Remote Access).

Do not port-forward port 8080 to the internet. If you need access away from
home, use a VPN (Tailscale, WireGuard) to connect to your home network first.

---

## Getting Help

- **docs/contributor-guide.md** — developer setup and conventions
- **docs/api-reference.md** — full daemon API reference
- **docs/architecture.md** — system diagrams and module explanations
- **references/error-taxonomy.md** — named error codes and what they mean
- **references/observability.md** — log events and metrics
- **DESIGN.md** — design system reference
