# Operator Quickstart — Zend Home on Home Hardware

This guide gets you from a fresh Raspberry Pi (or equivalent Linux machine) to a
running Zend Home daemon that you can pair your phone with. It is written for
someone who is comfortable with a terminal but does not want to read source code.

**Time estimate:** 15–20 minutes.

---

## What You Are Installing

Zend Home has two parts:

- **Daemon** (`daemon.py`) — a local HTTP service that runs on your home hardware.
  It presents a miner simulator in milestone 1 (a real miner backend plugs in later).
  It listens on `127.0.0.1:8080` by default.
- **CLI scripts** — shell wrappers that talk to the daemon. You run these from the
  Pi's terminal or SSH session.

Your phone or tablet does not do any mining. It only sends control commands to the
daemon running on this machine.

---

## Step 1 — Prepare the Machine

```bash
# Update package index
sudo apt update && sudo apt upgrade -y

# Install Python 3 and curl
sudo apt install -y python3 python3-pip curl git

# Verify Python version
python3 --version   # must be 3.10 or higher
```

---

## Step 2 — Get the Code

```bash
# Clone the repository
git clone <repo-url>
cd <repo-name>
```

---

## Step 3 — Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

You should see output like:

```
[INFO] Stopping daemon (if any)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. To stop it:

```bash
./scripts/bootstrap_home_miner.sh --stop
```

> ⚠️ **Warning — Do not set `ZEND_BIND_HOST=0.0.0.0`.** The daemon has no
> authentication in milestone 1. Binding to `0.0.0.0` exposes an unauthenticated
> miner control surface to your entire LAN. Any device on the network could then
> start, stop, or reconfigure your miner. The default `127.0.0.1` is safe because
> only processes on this machine can reach it.

---

## Step 4 — Verify the Daemon Is Running

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": ...}

curl http://127.0.0.1:8080/status
# Expected: miner snapshot with status, mode, hashrate, freshness
```

---

## Step 5 — Pair a Client

By default, clients are paired with `observe` capability (can read status but
cannot control the miner):

```bash
./scripts/pair_gateway_client.sh --client my-phone
```

For `observe,control` (full control):

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

---

## Step 6 — Read Miner Status

```bash
./scripts/read_miner_status.sh --client my-phone
```

Output includes:
- `status` — `running`, `stopped`, `offline`, or `error`
- `mode` — `paused`, `balanced`, or `performance`
- `hashrate_hs` — simulated hashrate in hashes/second
- `temperature` — simulated temperature in °C
- `uptime_seconds` — seconds since miner was started
- `freshness` — ISO timestamp of when this snapshot was taken

---

## Step 7 — Control the Miner

Requires `observe,control` capability:

```bash
# Start mining
./scripts/set_mining_mode.sh --client my-phone --action start

# Set to balanced mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Set to performance mode
./scripts/set_mining_mode.sh --client my-phone --mode performance

# Stop mining
./scripts/set_mining_mode.sh --client my-phone --action stop
```

Each control action appends a `control_receipt` event to the operations inbox.

---

## Step 8 — View the Operations Inbox

```bash
cd services/home-miner-daemon
python3 cli.py events --client my-phone
```

Or, to see only control receipts:

```bash
python3 cli.py events --client my-phone --kind control_receipt
```

---

## Step 9 — Keep the Daemon Running After Logout

The daemon started by `bootstrap_home_miner.sh` runs in the background of your
shell session. To keep it running after you log out, use `nohup` or `screen`:

```bash
# Option A: nohup
nohup bash -c './scripts/bootstrap_home_miner.sh' > ~/zend-daemon.log 2>&1 &

# Option B: screen
sudo apt install -y screen
screen -S zend -dm bash -c './scripts/bootstrap_home_miner.sh'
```

To reattach to a screen session later:

```bash
screen -r zend
```

---

## State Directory

All persistent state lives in `state/`:

| File | Contents |
|---|---|
| `state/principal.json` | Your shared identity (one per installation) |
| `state/pairing-store.json` | All paired devices and their capabilities |
| `state/event-spine.jsonl` | All operational events (plaintext JSONL) |
| `state/daemon.pid` | PID of the running daemon |

> ⚠️ **State directory permissions:** The state directory is created with the
> default system umask. On a shared system, other users may be able to read
> your pairing records and all operational events. On a single-user Raspberry Pi
> this is low risk. If you need higher isolation, run:
>
> ```bash
> chmod -R 700 state/
> ```

---

## Upgrading

```bash
git pull
# Restart the daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

> ⚠️ **Non-idempotent bootstrap:** `bootstrap_home_miner.sh` is not safe to run
> twice. If the daemon is already running and paired, `--stop` it first, then
> start fresh. See `docs/contributor-guide.md` for recovery steps.

---

## Uninstalling

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/
```

---

## Troubleshooting

### "Daemon failed to start" or port already in use

```bash
# Find and kill any process on port 8080
lsof -i :8080
kill <PID>
# Then retry
./scripts/bootstrap_home_miner.sh
```

### "Device 'alice-phone' already paired"

The bootstrap has already run and paired `alice-phone`. Either use the existing
paired device, or clear state and re-bootstrap:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -f state/pairing-store.json state/event-spine.jsonl
./scripts/bootstrap_home_miner.sh
```

### Daemon is running but CLI commands fail with "daemon_unavailable"

Check that `ZEND_DAEMON_URL` points to the right address:

```bash
echo $ZEND_DAEMON_URL   # should be http://127.0.0.1:8080
curl http://127.0.0.1:8080/health
```

If the daemon is bound to a different interface or port, set the env var:

```bash
export ZEND_DAEMON_URL=http://127.0.0.1:8080
```

### "This device lacks 'control' capability"

The device was paired with `observe`-only permissions. Re-pair with control:

```bash
# Note: this will fail if already paired. Clear state first (see above).
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

---

## Security Notes for Milestone 1

This is a LAN-only, no-auth daemon for milestone 1. Known limitations:

1. **No HTTP authentication** — the daemon accepts all requests on its bound
   interface. Keep `ZEND_BIND_HOST=127.0.0.1` (the default).
2. **No replay protection** — control commands cannot be replayed with the same
   effect, but there is no replay-prevention mechanism.
3. **Pairing tokens are cosmetic** — they expire at creation and are not
   cryptographically validated.
4. **Event spine is plaintext** — `state/event-spine.jsonl` is readable plain
   text, not encrypted.

These are honest gaps in milestone 1. They will be addressed in future releases.
