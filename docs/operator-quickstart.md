# Operator Quickstart

Deploy Zend on home hardware. This guide covers Raspberry Pi, mini PCs, or any
Linux box on your network.

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB free | 5 GB free |
| OS | Linux (any) | Raspberry Pi OS, Ubuntu Server |
| Network | Ethernet or WiFi | Ethernet |

Zend daemon is lightweight. A Raspberry Pi Zero works for testing; a Pi 3B+ or
better is recommended for production.

## Installation

### 1. Install Python

```bash
# Raspberry Pi OS / Debian / Ubuntu
sudo apt update
sudo apt install -y python3 python3-pip

# Verify
python3 --version  # Must be 3.10 or higher
```

### 2. Clone the Repository

```bash
git clone <repo-url> /opt/zend
cd /opt/zend
```

### 3. Verify the Install

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Configuration

The daemon reads these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use LAN IP for phone access) |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `./state` | Where to store principal and pairing data |

### Configure for LAN Access

To control Zend from your phone, bind to your LAN interface:

```bash
# Find your LAN IP
ip addr show | grep inet

# Example output:
# inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0

# Start with LAN binding
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

Or edit `scripts/bootstrap_home_miner.sh` and set the default:

```bash
BIND_HOST="${ZEND_BIND_HOST:-192.168.1.100}"
```

## First Boot

### 1. Start the Daemon

```bash
cd /opt/zend
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
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### 2. Open the Command Center

From your phone or tablet:

1. Connect to the same LAN
2. Open browser
3. Navigate to `http://<your-pi-ip>:8080/apps/zend-home-gateway/index.html`

Example: `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`

### 3. Pair Your Phone

The default device is already paired. To pair additional devices:

```bash
./scripts/pair_gateway_client.sh --client my-pixel --capabilities observe,control
```

## Daily Operations

### Check Miner Status

```bash
curl http://localhost:8080/status
```

Or via CLI:

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
# Note: daemon returns "MinerMode.BALANCED" in response

# Performance mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode performance
```

### View Operations Inbox

```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
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
WorkingDirectory=/opt/zend
ExecStart=/opt/zend/scripts/bootstrap_home_miner.sh --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zend-home
sudo systemctl start zend-home
```

Check status:

```bash
sudo systemctl status zend-home
```

## Recovery

### State is Corrupted

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

Port already in use:

```bash
# Find the process using the port
sudo lsof -i :8080

# Kill it
sudo kill <PID>

# Or use a different port
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

Daemon crashes immediately:

```bash
# Run in foreground to see errors
cd services/home-miner-daemon
python3 daemon.py
```

### Phone Can't Connect

1. Verify daemon is running:
   ```bash
   curl http://localhost:8080/health
   ```

2. Check the bind address:
   ```bash
   curl http://192.168.1.100:8080/health
   ```

3. Verify phone is on same network

4. Check firewall:
   ```bash
   sudo ufw allow 8080/tcp
   ```

## Security

### LAN-Only by Default

The daemon binds to a private interface. It does not expose:
- No public IP
- No cloud relay
- No internet-facing control surface

### Access Control

- `observe` capability: Read status only
- `control` capability: Change modes and start/stop

Default pairings start with `observe`. Grant `control` explicitly:

```bash
./scripts/pair_gateway_client.sh \
  --client trusted-phone \
  --capabilities observe,control
```

### What Not to Expose

- The daemon port (8080) should not be port-forwarded
- No authentication is implemented for milestone 1
- Treat your LAN as trusted

### Future Security

- Remote access via secure tunnel (post-milestone-1)
- Token-based authentication (post-milestone-1)
- TLS for daemon communication (post-milestone-1)

## Troubleshooting

### "Unable to connect to Zend Home"

1. Check daemon is running: `curl http://localhost:8080/health`
2. Check bind address: daemon must bind to LAN IP, not `127.0.0.1`
3. Check phone is on same network
4. Check firewall allows port 8080

### "Device lacks 'control' capability"

Your device only has `observe` capability. Pair again with control:

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### "already_running" or "already_stopped"

The miner simulator already has the requested state. This is normal.

### Freshness warning in browser

The daemon hasn't responded recently. This is normal if:
- The daemon just started
- The network is slow

If persistent, check the daemon is still running.

## Next Steps

- [Architecture Overview](architecture.md) — Understand how the system fits together
- [API Reference](api-reference.md) — All daemon endpoints
- [Design System](DESIGN.md) — Product design language
