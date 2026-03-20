# Command Center Client — Verification

**Lane:** `command-center-client:command-center-client`
**Slice:** Events and Inbox Functionality
**Generated:** 2026-03-20

## Automated Proof Commands

### Preflight Commands (from bootstrap)

```bash
./scripts/bootstrap_home_miner.sh
```

**Outcome:** PASS — Daemon started on 127.0.0.1:8080, principal created

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrap complete
```

---

```bash
./scripts/pair_gateway_client.sh --client alice-phone
```

**Outcome:** PASS — Client paired with observe capability

```
paired alice-phone
capability=observe
```

---

```bash
./scripts/read_miner_status.sh --client alice-phone
```

**Outcome:** PASS — MinerSnapshot returned with freshness

```
status=MinerStatus.STOPPED
mode=MinerMode.BALANCED
freshness=2026-03-20T19:02:10.396837+00:00
```

---

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

**Outcome:** PASS (expected failure) — Observe-only client cannot control

```
Error: Client lacks 'control' capability
```

---

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

**Outcome:** PASS — No local hashing detected

```
result: no local hashing detected
Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
```

---

### New Slice Verification Commands

```bash
# Fetch events via HTTP endpoint
curl -s "http://127.0.0.1:8080/events?limit=10" | python3 -m json.tool
```

**Outcome:** PASS — Returns events array with count

```json
{
    "events": [
        {
            "id": "8f0af76c-925b-4697-bd2d-b55ac502e525",
            "kind": "pairing_granted",
            "payload": {
                "device_name": "alice-phone",
                "granted_capabilities": ["observe"]
            },
            "created_at": "2026-03-20T19:02:10.267214+00:00",
            "version": 1
        }
    ],
    "count": 1
}
```

---

```bash
# Fetch events via shell script
./scripts/read_events.sh --client alice-phone --limit 10
```

**Outcome:** PASS — Formatted event listing

```
Events: 1

[2026-03-20T19:02:10.267214+00:00] pairing_granted
  device_name: alice-phone
  granted_capabilities: ['observe']
```

---

```bash
# Fetch events filtered by kind
curl -s "http://127.0.0.1:8080/events?kind=control_receipt" | python3 -m json.tool
```

**Outcome:** PASS — Returns empty array (no control_receipt events yet)

```json
{
    "events": [],
    "count": 0
}
```

---

```bash
# Verify invalid kind returns error
curl -s "http://127.0.0.1:8080/events?kind=invalid_kind"
```

**Outcome:** PASS — 400 error with invalid_kind message

```json
{
    "error": "invalid_kind",
    "message": "Unknown event kind: invalid_kind"
}
```

---

### Gateway HTML Verification

Open `apps/zend-home-gateway/index.html` in browser:

1. Navigate to **Home** tab — Status hero displays miner state
2. Navigate to **Inbox** tab — Events fetched and displayed (if any exist)
3. Navigate to **Device** tab — Shows device name and permissions
4. Navigate to **Agent** tab — Shows "Hermes not connected"

## Pre-existing Issues

- Daemon startup error (`OSError: Address already in use`) when daemon already running — scripts handle this gracefully
- Event spine plaintext JSON (not encrypted) — deferred for milestone 2
- No automated tests — planned for future slice

## Summary

| Command | Status |
|---------|--------|
| Bootstrap | PASS |
| Pair client | PASS |
| Read status | PASS |
| Set mode (unauthorized expected) | PASS |
| No local hashing audit | PASS |
| GET /events | PASS |
| read_events.sh | PASS |
| Gateway inbox display | PASS (wired) |

All verification commands passed.