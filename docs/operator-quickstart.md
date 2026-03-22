# Operator Quickstart — Zend Home on Home Hardware

This guide deploys the Zend Home Miner daemon on a Linux machine in your home
— a Raspberry Pi, a mini PC, a NAS, or any machine running Linux with Python
3.10+.

**Assumption**: you want to run the daemon on a machine on your home network,
pair it with a phone or browser client, and control your home miner from that
device.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Any Linux-capable ARM or x86 | ARMv8+ or modern x86 |
| RAM | 256 MB | 512 MB |
| Storage | 100 MB | 1 GB |
| OS | Linux (Raspbian, Ubuntu, Debian) | Debian 12 or Ubuntu 22.04 LTS |
| Network | Ethernet or Wi-Fi, LAN access | Ethernet |
| Python | 3.10+ | 3.10+ (stdlib only) |

A Raspberry Pi 3B+ or later works. No GPU required — the milestone 1 daemon
is a simulator that does not perform actual mining work.

---

## Installation

### 1. Clone the Repository

SSH into your machine and clone:

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python

```bash
python3 --version
# Must be 3.10 or later
```

### 3. No pip install Required

Zend ships with no external dependencies. All imports are from Python's
standard library. If `python3 --version` passes, you are ready.

---

## Configuration

Environment variables control daemon behavior. Set them before running
`bootstrap_home_miner.sh`.

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `<repo>/state` | Where state files live |
| `ZEND_BIND_HOST` | `127.0.0.1` | IP the daemon binds to |
| `ZEND_BIND_PORT` | `8080` | Port the daemon listens on |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Full URL for CLI commands |
| `ZEND_TOKEN_TTL_HOURS` | (not set) | Token expiration (future use) |

### LAN Binding (Required for Phone Access)

The default (`127.0.0.1`) binds only to localhost. To access the daemon from
another device on your LAN, set `ZEND_BIND_HOST` to your machine's LAN IP or
`0.0.0.0` (all interfaces):

```bash
# Find your LAN IP
hostname -I | awk '{print $1}'
# Example output: 192.168.1.100

# Run with LAN binding
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

**Security note**: Binding to `0.0.0.0` exposes the daemon to all LAN devices.
Only devices on your trusted LAN can reach it. Do not expose this port to the
internet.

---

## First Boot

### 1. Run Bootstrap

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 192.168.1.100:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

### 2. Verify the Daemon Is Running

From the same machine:

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

From another machine on the LAN:

```bash
curl http://192.168.1.100:8080/health
# Expected: same as above
```

---

## Pairing a Phone or Browser Client

The bootstrap script already paired a device named `alice-phone` with `observe`
capability. To pair additional devices:

```bash
# Pair with observe capability only
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe

# Pair with observe AND control capability
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
  "paired_at": "2026-03-22T..."
}
```

### Capability Reference

| Capability | What It Allows |
|---|---|
| `observe` | Read miner status and health |
| `control` | Start, stop, or change mining mode |

---

## Opening the Command Center

On your phone or tablet:

1. Open a browser (Chrome, Safari, Firefox).
2. Navigate to `http://192.168.1.100:8080` — **this will fail** because the
   daemon serves an API, not HTML.

The HTML command center is a **local file** that you open in your browser:

1. Copy `apps/zend-home-gateway/index.html` to your phone (via file share,
   AirDrop, or a local web server).
2. Open it in your browser.

**Or**, serve the file with a simple local server:

```bash
# On the daemon machine:
cd apps/zend-home-gateway
python3 -m http.server 8081
```

Then on your phone: open `http://192.168.1.100:8081/index.html`.

The command center connects to the daemon at `http://127.0.0.1:8080`. **You must
update the `API_BASE` constant in the HTML file** to your LAN IP:

```javascript
// Near the top of the <script> section in index.html
const API_BASE = 'http://192.168.1.100:8080';
```

After saving, open the file in your browser. The Home tab should show live
miner status.

---

## Daily Operations

### Check Miner Status

```bash
# Via CLI (requires observe capability)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Via HTTP directly
curl http://127.0.0.1:8080/status
```

### Start Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start
```

### Stop Mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop
```

### Change Mining Mode

```bash
# Pause all mining work
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode paused

# Balanced (moderate work, moderate heat)
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced

# Performance (maximum work)
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode performance
```

### View Events (Receipts, Alerts, Summaries)

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone --kind all --limit 10

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 5
```

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

---

## Daemon Lifecycle

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
# Or for LAN access:
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check If Daemon Is Running

```bash
./scripts/bootstrap_home_miner.sh --status
```

### View Daemon Logs

The daemon prints to stdout. If started via `bootstrap_home_miner.sh`, the
background process output is not captured. To log to a file:

```bash
ZEND_STATE_DIR="$PWD/state" \
  ZEND_BIND_HOST=192.168.1.100 \
  ZEND_BIND_PORT=8080 \
  python3 services/home-miner-daemon/daemon.py > daemon.log 2>&1 &
echo $! > state/daemon.pid
```

---

## Recovery

### Daemon Won't Start — Port Already in Use

```bash
# Find what's using port 8080
lsof -i :8080
# or
ss -tlnp | grep 8080

# Kill it
kill <PID>

# Retry bootstrap
./scripts/bootstrap_home_miner.sh
```

### State Is Corrupted

If `state/` files are corrupted or the daemon behaves unexpectedly:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Re-bootstrap (creates fresh state)
./scripts/bootstrap_home_miner.sh
```

This is safe. The daemon is stateless — all durable state is in `state/`. A
clean start produces a new `PrincipalId` and empty pairing/event stores.

### Phone Can't Reach the Daemon

1. Verify the daemon is running: `curl http://127.0.0.1:8080/health`
2. Verify the LAN IP is correct: `hostname -I`
3. Check the phone is on the same LAN subnet.
4. Check that the command center's `API_BASE` URL matches the daemon's LAN IP.
5. Check for firewall rules: `sudo ufw status` — ensure the daemon port is
   allowed on the LAN interface.

### Pairing Fails with "already paired"

```bash
# List all paired devices in state/pairing-store.json
cat state/pairing-store.json

# Remove a device (edit state/pairing-store.json and delete the entry)
# Then re-pair:
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

---

## Security Notes

- **LAN-only by design**: the daemon is not intended for internet exposure in
  milestone 1. Keep it behind your router's firewall.
- **No authentication on the daemon itself**: pairing and capability scoping
  handle authorization. Do not add a public port mapping for `8080`.
- **Event spine is plaintext JSONL in milestone 1**: real encryption is
  deferred. The event spine lives in `state/event-spine.jsonl` which is in
  `.gitignore` and not committed. For home use this is acceptable.
- **Token expiration**: not yet enforced. Future versions will add time-limited
  pairing tokens.
- **Control requires explicit grant**: a device without `control` capability
  cannot start, stop, or change the miner mode, even if it can reach the
  daemon.

---

## What's Next

After milestone 1, these features are planned:

- Real mining backend (the current daemon is a simulator)
- Remote access via secure tunnel (not direct internet exposure)
- Hermes agent integration through the Zend adapter
- Encrypted inbox for private messaging
- Payout-target configuration (higher safety bar than mode changes)
