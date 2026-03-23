# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Status:** Spec — ready for implementation
**Created:** 2026-03-23
**Repo:** `services/home-miner-daemon/`

---

## Purpose / User-Visible Outcome

After this slice lands, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine—but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the daemon's inbox, and verify that control attempts are rejected with `HERMES_UNAUTHORIZED`.

## Scope of This Slice

The first Hermes slice is intentionally narrow. It establishes the **trust boundary** between Hermes and the daemon but does not wire Hermes into the wider system beyond that boundary.

In scope:
- `services/home-miner-daemon/hermes.py` — the adapter module
- Hermes-specific pairing records in `services/home-miner-daemon/store.py`
- Hermes HTTP endpoints in `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/tests/test_hermes.py` — boundary tests

Out of scope for this slice:
- Hermes inbox message access (later: Hermes reads its own inbox events)
- Hermes control capability (requires separate approval flow)
- Hermes direct miner commands
- Remote access beyond LAN
- UI changes (Agent tab deferred to a later lane)

---

## Architecture

```
Hermes Agent
     |
     | HTTPS (LAN)
     v
Zend Home Miner Daemon
     |
     +-- miner (MinerSimulator)          # status, start, stop, set_mode
     +-- spine (event spine)            # append-only journal
     +-- store (pairing + principal)    # identity + capability records
     +-- hermes (HERMES ADAPTER)         # NEW: Hermes-specific boundary
```

The adapter is the only path Hermes uses to interact with the daemon. All Hermes requests pass through it before reaching any privileged daemon behavior. The adapter enforces:

1. **Token validation** — authority tokens are base64-encoded JSON signed by the daemon's secret; the adapter validates signature, expiration, and Hermes-specific capability claims.
2. **Capability checking** — Hermes may `observe` (read status) and `summarize` (append summaries); it may not `control`.
3. **Event filtering** — `user_message`, `pairing_requested`, `pairing_granted`, and `capability_revoked` events are stripped from Hermes event reads.
4. **Payload transformation** — fields that Hermes should not see are removed before the response is returned.

---

## Hermes Capability Model

Hermes capabilities are **independent** from gateway device capabilities. The gateway uses `observe` and `control`. Hermes uses `observe` and `summarize`.

```python
HERMES_CAPABILITIES = ["observe", "summarize"]
```

```python
HERMES_READABLE_EVENTS = [
    "hermes_summary",   # Hermes's own summaries
    "miner_alert",       # Alerts from the miner
    "control_receipt",   # Control command receipts (for auditing)
]
```

```python
HERMES_BLOCKED_EVENTS = [
    "user_message",
    "pairing_requested",
    "pairing_granted",
    "capability_revoked",
]
```

**Rationale:** Hermes is an observer and summarizer, not a controller. Its summaries are what appear in the daemon's inbox for human review. It must not see user messages (privacy boundary) and must not see pairing events (security boundary for the pairing trust graph).

---

## Authority Token

The daemon issues authority tokens to Hermes during the pairing flow. The token encodes what Hermes is allowed to do and is signed by the daemon so it cannot be forged by a third party.

### Token Structure

```python
@dataclass
class HermesAuthorityToken:
    principal_id: str      # matches the daemon's principal
    hermes_id: str         # stable Hermes identity (e.g. "hermes-001")
    capabilities: list     # subset of HERMES_CAPABILITIES
    expires_at: str        # ISO 8601 UTC
    issued_at: str         # ISO 8601 UTC
    signature: str         # HMAC-SHA256 of the above fields, base64-encoded
```

### Token Lifecycle

1. **Pairing** (`POST /hermes/pair`): Daemon generates a Hermes pairing record with `hermes_id`, `device_name="hermes:<hermes_id>"`, and capabilities `["observe", "summarize"]`. A pairing token is stored in `store.py` alongside the record.

2. **Connect** (`POST /hermes/connect`): Hermes presents the pairing token. The daemon validates it, wraps it in a signed `HermesAuthorityToken`, and returns the token string (not just the pairing record). The token is stored in `store.py` keyed by `hermes_id` so subsequent requests can be validated.

3. **Request**: Hermes sends `Authorization: Hermes <hermes_id>` and includes the authority token in the request body. The adapter validates the signature, checks expiration, and enforces the capability list.

4. **Expiration / Revocation**: Expired tokens are rejected. A revoked Hermes (removed from the pairing store) cannot connect even with a well-formed token.

### Token Validation Rules (in `hermes.py`)

```python
def validate_authority_token(token: HermesAuthorityToken) -> None:
    """Validate token. Raises on failure."""
    # 1. Check expiration
    if datetime.fromisoformat(token.expires_at.replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise TokenExpiredError("HERMES_TOKEN_EXPIRED")

    # 2. Check capabilities
    for cap in token.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise TokenInvalidError(f"HERMES_TOKEN_INVALID: unknown capability '{cap}'")

    # 3. Check signature
    expected_sig = _sign_token(token)
    if not hmac.compare_digest(token.signature, expected_sig):
        raise TokenInvalidError("HERMES_TOKEN_INVALID: signature mismatch")

    # 4. Check Hermes is still paired
    if not store.is_hermes_paired(token.hermes_id):
        raise HermesNotPairedError("HERMES_NOT_PAIRED")
```

---

## API Contract

### `HermesConnection` (returned by `connect()`)

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list       # ["observe", "summarize"]
    connected_at: str        # ISO 8601 UTC
    token: HermesAuthorityToken
```

### `connect(authority_token: str) -> HermesConnection`

Parses and validates the authority token, then returns a `HermesConnection`. Does not persist connection state — each request is stateless and re-validates.

| Condition | Raised |
|-----------|--------|
| Token structure invalid (not base64 JSON) | `ValueError` |
| Token signature invalid | `TokenInvalidError` |
| Token expired | `TokenExpiredError` |
| Capability not in `HERMES_CAPABILITIES` | `TokenInvalidError` |
| Hermes not in pairing store | `HermesNotPairedError` |
| Capability missing for operation | `PermissionError("HERMES_UNAUTHORIZED")` |

### `read_status(connection: HermesConnection) -> dict`

Requires `observe` capability. Returns `miner.get_snapshot()` directly.

```python
# Returns:
{
    "status": "running",
    "mode": "balanced",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 120,
    "freshness": "2026-03-23T12:00:00Z"
}
```

Raises `PermissionError("HERMES_UNAUTHORIZED: observe capability required")` if `observe` not in connection capabilities.

### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent`

Requires `summarize` capability. Appends a `hermes_summary` event to the spine and returns it.

```python
# Spine event payload:
{
    "summary_text": "...",
    "authority_scope": "observe",
    "generated_at": "2026-03-23T12:00:00Z"
}
```

Raises `PermissionError("HERMES_UNAUTHORIZED: summarize capability required")` if `summarize` not in connection capabilities.

### `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[SpineEvent]`

Returns events Hermes is allowed to read, with `user_message`, `pairing_requested`, `pairing_granted`, and `capability_revoked` filtered out. Returns events from spine in reverse-chronological order.

---

## HTTP Endpoints (in `daemon.py`)

All Hermes endpoints are under `/hermes/` and use `Authorization: Hermes <hermes_id>` header (distinct from gateway device auth).

### `POST /hermes/pair`

Create a Hermes pairing record. No auth required (pairing is done in a trusted setup context).

**Request body:**
```json
{
    "hermes_id": "hermes-001",
    "device_name": "hermes-agent"
}
```

**Response (201):**
```json
{
    "hermes_id": "hermes-001",
    "device_name": "hermes:hermes-001",
    "capabilities": ["observe", "summarize"],
    "pairing_token": "<uuid-token>",
    "paired_at": "2026-03-23T12:00:00Z"
}
```

### `POST /hermes/connect`

Accept a pairing token, validate it, and return a signed authority token.

**Request body:**
```json
{
    "pairing_token": "<uuid-token>",
    "hermes_id": "hermes-001"
}
```

**Response (200):**
```json
{
    "connected": true,
    "authority_token": "<base64-signed-token>",
    "connection": {
        "hermes_id": "hermes-001",
        "principal_id": "...",
        "capabilities": ["observe", "summarize"],
        "connected_at": "2026-03-23T12:00:00Z"
    }
}
```

### `GET /hermes/status`

Read miner status. Requires `Authorization: Hermes <hermes_id>` header.

**Response (200):** Miner snapshot dict.

**Error (403):** `HERMES_UNAUTHORIZED: observe capability required`

### `POST /hermes/summary`

Append a Hermes summary. Requires Hermes auth header.

**Request body:**
```json
{
    "summary_text": "Miner running normally at 50kH/s",
    "authority_scope": "observe"
}
```

**Response (201):**
```json
{
    "appended": true,
    "event_id": "<uuid>"
}
```

**Error (403):** `HERMES_UNAUTHORIZED: summarize capability required`

### `GET /hermes/events`

Read filtered events (blocked kinds stripped). Requires Hermes auth header.

**Query params:** `?limit=20`

**Response (200):** List of SpineEvent dicts.

---

## Error Codes

| Code | Meaning |
|------|---------|
| `HERMES_UNAUTHORIZED` | Missing required capability |
| `HERMES_TOKEN_INVALID` | Token structure or signature invalid |
| `HERMES_TOKEN_EXPIRED` | Token has passed its expiry time |
| `HERMES_NOT_PAIRED` | Hermes ID not registered in pairing store |

---

## Store Changes

In `store.py`, add:

```python
HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')

@dataclass
class HermesPairing:
    hermes_id: str
    device_name: str           # always "hermes:<hermes_id>"
    principal_id: str
    capabilities: list         # ["observe", "summarize"]
    pairing_token: str        # the token Hermes uses to connect
    paired_at: str
    token_expires_at: str

def load_hermes_pairings() -> dict: ...
def save_hermes_pairings(pairings: dict): ...
def create_hermes_pairing(hermes_id: str, device_name: str) -> HermesPairing: ...
def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]: ...
def is_hermes_paired(hermes_id: str) -> bool: ...
def get_hermes_authority_token(hermes_id: str) -> Optional[HermesAuthorityToken]: ...
def store_hermes_authority_token(hermes_id: str, token: HermesAuthorityToken): ...
```

---

## Tests

`services/home-miner-daemon/tests/test_hermes.py` covers:

1. `test_hermes_pairing` — `POST /hermes/pair` creates a record
2. `test_hermes_connect_valid_token` — connect flow succeeds with valid token
3. `test_hermes_connect_expired_token` — rejects with `HERMES_TOKEN_EXPIRED`
4. `test_hermes_connect_unknown_hermes` — rejects with `HERMES_NOT_PAIRED`
5. `test_hermes_read_status_authorized` — returns miner snapshot
6. `test_hermes_read_status_unauthorized` — 403 without observe cap
7. `test_hermes_append_summary_authorized` — appends event, returns event_id
8. `test_hermes_append_summary_unauthorized` — 403 without summarize cap
9. `test_hermes_events_filter_user_messages` — user_message events absent from response
10. `test_hermes_events_filter_pairing_events` — pairing_requested/granted absent
11. `test_hermes_control_rejected` — `POST /miner/start` with Hermes auth returns 403

---

## Acceptance Criteria

| # | Criterion | Test |
|---|-----------|------|
| 1 | `POST /hermes/pair` creates a Hermes pairing with observe+summarize capabilities | `test_hermes_pairing` |
| 2 | `POST /hermes/connect` returns a signed authority token for a valid pairing token | `test_hermes_connect_valid_token` |
| 3 | Expired tokens are rejected with `HERMES_TOKEN_EXPIRED` | `test_hermes_connect_expired_token` |
| 4 | `GET /hermes/status` returns miner snapshot when Hermes has observe cap | `test_hermes_read_status_authorized` |
| 5 | `GET /hermes/status` returns 403 when Hermes lacks observe cap | `test_hermes_read_status_unauthorized` |
| 6 | `POST /hermes/summary` appends a `hermes_summary` event to the spine | `test_hermes_append_summary_authorized` |
| 7 | `POST /hermes/summary` returns 403 without summarize cap | `test_hermes_append_summary_unauthorized` |
| 8 | `GET /hermes/events` excludes `user_message` events | `test_hermes_events_filter_user_messages` |
| 9 | `GET /hermes/events` excludes `pairing_requested` and `pairing_granted` | `test_hermes_events_filter_pairing_events` |
| 10 | Control commands (`POST /miner/start`) with Hermes auth return 403 | `test_hermes_control_rejected` |

---

## Proof of Implementation (manual verification)

```bash
# Start daemon
python services/home-miner-daemon/daemon.py &

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'

# Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "pairing_token": "<token-from-above>"}'
# Save authority_token from response

# Read status (replace <token>)
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'

# Read filtered events
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Authority-Token: <token>"

# Attempt control (should be rejected at daemon level, not Hermes level)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Expected: 403 or 404 (not a Hermes endpoint)
```
