# Zend

Zend is a private command center for a home mining node. The phone is the
control plane; the home miner is the workhorse. Mining does not happen on the
phone. Encrypted messaging uses Zcash shielded memo transport.

**Zend Home** is the first product slice: a thin mobile-shaped command center,
a LAN-paired home miner daemon, a private event spine, and an encrypted
operations inbox — all running on Python 3.10+ with no external dependencies.

---

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and pair a default device
./scripts/bootstrap_home_miner.sh

# 3. Verify the daemon is healthy
python3 services/home-miner-daemon/cli.py health

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Start mining (or set mode: paused | balanced | performance)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

Open `apps/zend-home-gateway/index.html` in your browser for the mobile command
center UI.

---

## Architecture

```
  Browser / Phone               Linux Machine (Home Server)
  ─────────────────             ───────────────────────────
  index.html                    home-miner-daemon/
    ├─ fetches /status            ├─ daemon.py  (HTTP server + MinerSimulator)
    ├─ POST /miner/start          ├─ cli.py     (all terminal commands)
    ├─ POST /miner/stop           ├─ store.py   (PrincipalId + pairing records)
    └─ POST /miner/set_mode      ├─ spine.py    (append-only event journal)
                                  └─ state/     (principal.json, pairing-store.json,
                                                 event-spine.jsonl)
```

The daemon binds to `127.0.0.1:8080` by default (LAN-only). Set
`ZEND_BIND_HOST="0.0.0.0"` in your shell to allow phone access from the same
network.

---

## Directory Structure

```
zend/
├── apps/zend-home-gateway/
│   └── index.html           Mobile-shaped command center (open in browser)
│
├── services/home-miner-daemon/
│   ├── daemon.py            LAN-only HTTP server + miner simulator
│   ├── cli.py               Terminal commands: health, status, bootstrap,
│   │                        pair, control, events
│   ├── store.py             PrincipalId and capability-scoped pairing store
│   └── spine.py             Append-only encrypted event spine (JSONL)
│
├── scripts/
│   ├── bootstrap_home_miner.sh   Start daemon, create principal, emit token
│   ├── pair_gateway_client.sh    Pair a named device with capabilities
│   ├── read_miner_status.sh      Read live miner snapshot
│   ├── set_mining_mode.sh        Change operating mode
│   ├── hermes_summary_smoke.sh   Prove Hermes adapter integration
│   └── no_local_hashing_audit.sh Prove no hashing on the client device
│
├── state/                   Runtime state (daemon.pid, pairing-store.json,
│   └── README.md            event-spine.jsonl). Disposable. Untracked.
│
├── docs/
│   ├── architecture.md       System diagrams and module explanations
│   ├── contributor-guide.md  Dev setup, coding conventions, submitting changes
│   ├── operator-quickstart.md  Home hardware deployment guide
│   └── api-reference.md      Every endpoint with curl examples
│
├── references/
│   ├── inbox-contract.md     Shared PrincipalId contract
│   ├── event-spine.md       Event kinds, schema, append behavior
│   ├── error-taxonomy.md     Named error classes for milestone 1
│   ├── hermes-adapter.md    Hermes adapter contract
│   └── observability.md      Structured log events and metrics
│
├── specs/                   Durable capability and decision specs
├── plans/                   Executable implementation plans (ExecPlans)
└── DESIGN.md                Visual and interaction design system
```

---

## Prerequisites

- **Python 3.10 or later.** No pip install, no virtual environment, no external
  packages. The standard library is all you need.
- **Linux** (Ubuntu 22.04+, Raspberry Pi OS, or similar)
- **A browser** for the command center UI (Chrome, Firefox, Safari, Edge)

Verify Python:

```bash
python3 --version  # Python 3.10.12  (or later)
```

---

## Running Tests

Install pytest (one-time):

```bash
pip install pytest
```

Run the test suite:

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

---

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

---

## Key Design Points

- **No mining on the phone.** The `index.html` file is a pure control surface.
  No hashing, no CPU work, no WebAssembly.
- **LAN-only by default.** The daemon binds to `127.0.0.1`. Set
  `ZEND_BIND_HOST="0.0.0.0"` for LAN access from your phone.
- **Stdlib only.** Zero pip dependencies. Python 3.10 stdlib is sufficient.
- **Append-only event spine.** All operations are recorded in
  `state/event-spine.jsonl`. The inbox is a derived view of the spine.
- **Capability-scoped pairing.** Devices are paired with `observe` (read-only)
  or `control` (read + operate) permissions.

---

## Finding Out More

| What you need | Where to look |
|--------------|---------------|
| How the system works | `docs/architecture.md` |
| Dev setup and coding | `docs/contributor-guide.md` |
| Deploy on home hardware | `docs/operator-quickstart.md` |
| Every API endpoint | `docs/api-reference.md` |
| Design system | `DESIGN.md` |
| Current implementation plan | `plans/2026-03-19-build-zend-home-command-center.md` |
| Spec writing rules | `SPEC.md` |
| Plan writing rules | `PLANS.md` |
