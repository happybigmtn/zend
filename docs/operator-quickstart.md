# Operator Quickstart — Home Hardware Deployment

**For:** Home operators running Zend on a Raspberry Pi, home server, or desktop
**Prerequisites:** Python 3.9+, git, curl. No Docker required.

---

## What You Are Deploying

Zend has two parts:

1. **The daemon** — a LAN-only control service that runs on your home hardware.
   This is the "home miner" in the product description.
2. **The gateway client** — a thin mobile-shaped web UI you open in a browser.
   This is the "phone as control plane" part.

Mining happens on the machine running the daemon. The client device (phone or
laptop) only sends commands and reads status — it never mines.

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Any modern 64-bit | ARMv8 or x86-64 |
| RAM | 512 MB | 1 GB+ |
| Disk | 100 MB free | 1 GB+ free |
| Network | Ethernet or Wi-Fi on LAN | Ethernet |
| OS | Raspberry Pi OS 12+, Ubuntu 22.04+, macOS 13+ | Same |

A Raspberry Pi 4 or any low-power home server is sufficient for milestone 1.
The daemon does not require a GPU.

## Network Setup

The daemon binds **LAN-only** by default. This means:

- It listens only on the private IP address you specify (e.g., `192.168.1.100`).
- It does **not** open any port on your public IP.
- Devices on the same home network can reach it; devices outside your network cannot.
- No cloud service, relay, or tunnel is involved.

You must know your machine's LAN IP address. Common ways to find it:

```bash
# Linux
ip addr show | grep 'inet '

# macOS
ipconfig getifaddr en0

# Router web interface — look for "connected devices"
```

In this guide, we use `192.168.1.100` as the example LAN IP. Replace it with
your actual address.

## Step 1 — Install Zend

On your home hardware machine:

```bash
# Clone the repository
git clone <zend-repo-url>
cd zend
```

No other installation steps are required. Zend uses only Python 3 from the
standard library.

## Step 2 — Start the Daemon

### Option A: Localhost only (default — for testing on the same machine)

```bash
./scripts/bootstrap_home_miner.sh
```

The daemon starts on `127.0.0.1:8080`. Only processes on the same machine can
reach it.

### Option B: LAN binding (for accessing from phone/laptop on the same network)

```bash
ZEND_BIND_HOST=192.168.1.100 ZEND_BIND_PORT=8080 ./scripts/bootstrap_home_miner.sh
```

Replace `192.168.1.100` with your machine's LAN IP address.

### Verify the daemon is running

```bash
curl http://127.0.0.1:8080/health
# or, for LAN:
curl http://192.168.1.100:8080/health
```

Expected response:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 12}
```

## Step 3 — Pair a Client

From your phone or laptop browser, open the gateway client:

```
file://<path-to-repo>/apps/zend-home-gateway/index.html
```

Or serve it with a simple local server:

```bash
cd apps/zend-home-gateway && python3 -m http.server 9000
# Then open: http://192.168.1.100:9000
```

On first load, the client prompts you through the pairing flow. The daemon
already has a default pairing for `alice-phone` created during bootstrap.

To pair a new device from the terminal:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

- `observe` — read miner status only
- `control` — start, stop, and change miner mode

## Step 4 — Read Miner Status

From any machine on your LAN:

```bash
curl http://192.168.1.100:8080/status
```

Or via the CLI:

```bash
./scripts/read_miner_status.sh --client alice-phone
```

The response includes:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00Z"
}
```

The `freshness` field confirms the data is live.

## Step 5 — Control the Miner

Start mining:

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start
```

Set a mode:

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

Valid modes: `paused`, `balanced`, `performance`.

After any control action, a receipt is appended to the event spine. Check the
inbox in the gateway client to see it.

## Where Data Lives

| What | Where |
|---|---|
| Principal identity | `state/principal.json` |
| Paired clients + capabilities | `state/pairing-store.json` |
| All events (source of truth) | `state/event-spine.jsonl` |
| Running daemon PID | `state/daemon.pid` |

The `state/` directory is local to this machine and is not synced anywhere.
Only you own this data.

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or, if the daemon is running in the background and you know its PID:

```bash
kill $(cat state/daemon.pid)
```

## Resetting State

If you need a completely fresh start:

```bash
# 1. Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# 2. Wipe state
rm -rf state/*

# 3. Restart and bootstrap
./scripts/bootstrap_home_miner.sh
```

## What LAN-Only Means in Plain Language

Your daemon is **not** accessible from the internet. It binds only to your
home network IP address. If someone outside your LAN tries to connect, their
connection is silently refused at the network layer — there is no exposed
service to exploit.

In milestone 1, there is no remote access feature. To control your miner from
outside your home network, you would need a VPN or SSH tunnel — not provided by
Zend in milestone 1.

## What the Event Spine Is

Every time something happens — a client pairs, a control command is issued, an
alert fires — it is written to `state/event-spine.jsonl` as an encrypted JSON
record. This is the single source of truth for all Zend operational history.
The inbox in the gateway client is just a view of this file.

## Troubleshooting

### Daemon won't start — port already in use

```bash
# Find what's using port 8080
lsof -i :8080
# or
ss -tlnp | grep 8080
```

Stop the conflicting process, or set a different port:

```bash
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

### Client can't reach the daemon on LAN

1. Verify the daemon is running: `curl http://192.168.1.100:8080/health` from
   the host machine.
2. Verify your phone is on the same LAN subnet (not guest Wi-Fi).
3. Check that any firewall on the host machine allows inbound on the chosen port:
   ```bash
   sudo ufw allow 8080/tcp  # Ubuntu/Debian
   ```

### Miner shows as "offline" in the client

The daemon is running but the miner simulator is in the offline state. In
milestone 1, the daemon ships with a built-in simulator. The `status`
endpoint returns simulated data. A real miner backend integration comes in a
later milestone.

### I lost my pairing record

Wipe `state/pairing-store.json` and re-pair:

```bash
rm state/pairing-store.json
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```
