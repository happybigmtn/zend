# Operator Quickstart

Deploy and operate Zend Home Miner on your own hardware. This guide covers
home-server or single-board-computer deployments.

## Hardware Requirements

- **Processor:** Any modern CPU. The milestone 1 daemon is a Python simulator;
  real miner backends do the hashing work off this machine.
- **Memory:** 512 MB RAM minimum.
- **Storage:** 100 MB for state files and logs.
- **Network:** Ethernet recommended. WiFi supported but Ethernet is more
  reliable for a always-on home service.
- **OS:** Linux (Ubuntu 22.04+ recommended), macOS, or any POSIX system with
  Python 3.8+.

## Known Limitations (Milestone 1)

Read this before deploying. These are not bugs — they are known gaps in
milestone 1:

1. **No daemon authentication.** The HTTP daemon accepts all requests. LAN-only
   binding is the only access control.
2. **Event spine is plaintext.** `state/event-spine.jsonl` is plain JSONL.
   Anyone with file access can read pairing records, control commands, and
   principal identities.
3. **Pairing tokens never expire.** A paired device retains access permanently.
   There is no revocation mechanism.
4. **Capability enforcement is at the CLI layer only.** Calling the daemon
   directly (e.g. `curl`) bypasses all `observe`/`control` checks.
5. **No TLS.** All daemon communication is plaintext HTTP.

Do not expose the daemon port to the internet or untrusted networks in
milestone 1.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd zend

# Verify Python 3
python3 --version
```

No build step. No pip install. Python 3 standard library only.

## Step 1 — Choose a Bind Address

The daemon binds to `127.0.0.1` (localhost only) by default. For a home
deployment where your phone or laptop will connect over the LAN, bind to your
machine's LAN IP address.

Find your LAN IP:

```bash
# Linux/macOS
ip addr show | grep "inet "
# or
hostname -I
```

Example: `192.168.1.100`.

**Important:** Do not bind to `0.0.0.0` on a network you don't control. Use the
explicit LAN address.

## Step 2 — Start the Daemon

```bash
# Bind to your LAN IP (replace with your actual IP)
export ZEND_BIND_HOST=192.168.1.100
export ZEND_BIND_PORT=8080

# Bootstrap: start daemon + create principal + pair first device
./scripts/bootstrap_home_miner.sh
```

Verify the daemon is running:

```bash
curl http://192.168.1.100:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Step 3 — Pair Your Gateway Client

From your phone or laptop, run:

```bash
# Adjust IP and port to match your deployment
export ZEND_DAEMON_URL=http://192.168.1.100:8080

# Pair with control capability (can start/stop/change mode)
./scripts/pair_gateway_client.sh \
  --client my-phone \
  --capabilities observe,control
```

Or pair with observe-only (can read status but not control):

```bash
./scripts/pair_gateway_client.sh \
  --client my-tablet \
  --capabilities observe
```

## Step 4 — Connect the Gateway UI

Open `apps/zend-home-gateway/index.html` in a browser on your phone or laptop.
The hardcoded `API_BASE` points to `http://127.0.0.1:8080` — you need to either:

**Option A — Edit the API_BASE** (quickest for a self-hosted deployment):

Edit line ~285 of `apps/zend-home-gateway/index.html`:
```javascript
const API_BASE = 'http://192.168.1.100:8080';
```

Then serve or open the file.

**Option B — Serve the UI over HTTPS** (recommended for production-adjacent):

The daemon has no TLS. For any non-localhost deployment, put a reverse proxy
in front of it:

```nginx
# /etc/nginx/sites-available/zend-home
server {
    listen 443 ssl;
    server_name zend-home.local;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://192.168.1.100:8080;
        proxy_set_header Host $host;
    }
}
```

Then set `API_BASE = 'https://zend-home.local'` in the HTML.

## Step 5 — Run the Miner

```bash
# Start mining
./scripts/set_mining_mode.sh --client my-phone --action start

# Or set a mode (paused / balanced / performance)
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Check status
./scripts/read_miner_status.sh --client my-phone
```

## Daemon Management

### Start on boot (systemd)

```bash
# /etc/systemd/system/zend-home.service
[Unit]
Description=Zend Home Miner Daemon
After=network.target

[Service]
Type=simple
User=zend
WorkingDirectory=/home/zend/zend
ExecStart=/usr/bin/python3 services/home-miner-daemon/daemon.py
Environment="ZEND_STATE_DIR=/home/zend/zend/state"
Environment="ZEND_BIND_HOST=192.168.1.100"
Environment="ZEND_BIND_PORT=8080"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zend-home
sudo systemctl status zend-home
```

### Logs

The daemon logs to stdout. With systemd:

```bash
journalctl -u zend-home -f
```

### Upgrade

```bash
cd /path/to/zend
git pull
sudo systemctl restart zend-home
```

State files in `state/` are preserved across upgrades. If a state format
migration is needed, it will be documented in the release notes.

### Reset

```bash
# Stop daemon
sudo systemctl stop zend-home

# Wipe state (irreversible — removes all pairing records and principal)
rm -rf /home/zend/zend/state/*

# Restart
sudo systemctl start zend-home

# Re-pair devices
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

## Security Checklist

Before deploying, confirm each of these:

- [ ] Daemon binds to a private LAN IP, not `0.0.0.0` and not a public IP
- [ ] No firewall rule allows port 8080 from the internet
- [ ] `state/` directory is readable only by the daemon user (`chmod 700`)
- [ ] `state/event-spine.jsonl` is world-unreadable (`chmod 600`)
- [ ] You understand milestone 1 has no daemon authentication
- [ ] You understand pairing tokens never expire and there is no revocation
- [ ] `API_BASE` in the gateway client points to your LAN IP, not a public URL

## Troubleshooting

### Daemon won't start — port already in use

```bash
# Find what's using port 8080
lsof -i :8080
# or
ss -tlnp | grep 8080

# Kill it or change ZEND_BIND_PORT
export ZEND_BIND_PORT=8081
./scripts/bootstrap_home_miner.sh
```

### Pairing fails — "already paired"

```bash
# Remove the existing pairing for that device name
# Edit state/pairing-store.json and remove the entry, then restart
```

### Status returns "unauthorized"

The CLI checks `observe` capability before calling the daemon. If the client was
paired with only `observe`, `read_miner_status.sh` will succeed. If it was not
paired at all, the capability check fails. Run `pair_gateway_client.sh` first.

### Gateway UI shows "Unable to connect"

- Daemon is not running → `sudo systemctl start zend-home`
- Wrong IP in `API_BASE` → edit `apps/zend-home-gateway/index.html`
- Browser CORS policy blocks the request → the daemon sends no CORS headers.
  The UI must be opened from `file://` or served from the same origin. Use a
  local HTTP server for the UI: `python3 -m http.server 9000 --directory apps/zend-home-gateway`

### Control action returns "unauthorized"

The client was paired with `observe` only. Re-pair with `control`:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```
