#!/usr/bin/env python3
"""
Zend Hermes Adapter

A scoped adapter that allows the Hermes AI agent to connect to the Zend
gateway with a narrow capability boundary. Hermes can observe miner status
and append summaries to the event spine, but cannot issue control commands
or read user messages.

The adapter sits between the external Hermes agent and the Zend gateway
contract, enforcing:
- Authority token validation (principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import spine
import store

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hermes capabilities are observe + summarize, independent from gateway
# observe + control. Hermes should never inherit gateway control capability.
HERMES_CAPABILITIES = ['observe', 'summarize']

# Hermes can read these event kinds from the spine.
# user_message is intentionally excluded to prevent Hermes from seeing
# private communications.
HERMES_READABLE_EVENTS = [
    spine.EventKind.HERMES_SUMMARY,
    spine.EventKind.MINER_ALERT,
    spine.EventKind.CONTROL_RECEIPT,
]

HERMES_EVENT_KINDS = [e.value for e in HERMES_READABLE_EVENTS]

# Token validity window (24 hours)
TOKEN_VALIDITY_SECONDS = 24 * 60 * 60


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HermesConnection:
    """Represents an active Hermes connection session."""
    hermes_id: str
    principal_id: str
    capabilities: list[str]       # subset of HERMES_CAPABILITIES
    connected_at: str             # ISO 8601
    token_expires_at: str         # ISO 8601

    def is_capable(self, capability: str) -> bool:
        """Check if connection has a specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HermesPairing:
    """A Hermes pairing record in the store."""
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str
    token_expires_at: str


@dataclass
class AuthorityToken:
    """Decoded authority token payload."""
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    expires_at: str
    issued_at: str


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", _default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

HERMES_PAIRING_FILE = os.path.join(STATE_DIR, 'hermes-pairing-store.json')
AUTHORITY_TOKEN_FILE = os.path.join(STATE_DIR, 'authority-tokens.jsonl')


def _load_hermes_pairings() -> dict:
    """Load all Hermes pairing records."""
    if os.path.exists(HERMES_PAIRING_FILE):
        with open(HERMES_PAIRING_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_hermes_pairings(pairings: dict):
    """Save Hermes pairing records."""
    with open(HERMES_PAIRING_FILE, 'w') as f:
        json.dump(pairings, f, indent=2)


def _load_authority_tokens() -> list[dict]:
    """Load authority tokens from the journal."""
    tokens = []
    if os.path.exists(AUTHORITY_TOKEN_FILE):
        with open(AUTHORITY_TOKEN_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    tokens.append(json.loads(line))
    return tokens


def _save_authority_token(token_data: dict):
    """Append an authority token record to the journal."""
    with open(AUTHORITY_TOKEN_FILE, 'a') as f:
        f.write(json.dumps(token_data) + '\n')


def decode_authority_token(token_str: str) -> AuthorityToken:
    """
    Decode and validate an authority token.

    In milestone 1, the token is a simple JSON payload encoded as base64.
    Production would use signed JWTs.

    Raises ValueError if token is malformed, expired, or has wrong capabilities.
    """
    try:
        import base64
        # Handle both raw JSON and base64-encoded JSON
        try:
            payload_bytes = base64.b64decode(token_str)
            payload = json.loads(payload_bytes)
        except Exception:
            # Try as raw JSON for development
            payload = json.loads(token_str)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"HERMES_INVALID_TOKEN: token is malformed ({e})")

    required_fields = ['hermes_id', 'principal_id', 'capabilities', 'expires_at']
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"HERMES_INVALID_TOKEN: missing required field '{field}'")

    # Validate capabilities
    for cap in payload['capabilities']:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: '{cap}' is not a valid Hermes capability. "
                f"Valid capabilities: {HERMES_CAPABILITIES}"
            )

    # Check expiration
    expires = datetime.fromisoformat(payload['expires_at'])
    now = datetime.now(timezone.utc)
    # Make expires timezone-aware if it's not
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires <= now:
        raise ValueError("HERMES_TOKEN_EXPIRED: authority token has expired")

    return AuthorityToken(
        hermes_id=payload['hermes_id'],
        principal_id=payload['principal_id'],
        capabilities=payload['capabilities'],
        expires_at=payload['expires_at'],
        issued_at=payload.get('issued_at', now.isoformat())
    )


def is_token_expired(token_expires_at: str) -> bool:
    """Check if a token has expired."""
    expires = datetime.fromisoformat(token_expires_at)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing:
    """
    Create a Hermes pairing record with observe + summarize capabilities.

    Pairing is idempotent: if hermes_id already exists, returns the
    existing record with a refreshed token.
    """
    principal = store.load_or_create_principal()
    pairings = _load_hermes_pairings()

    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + TOKEN_VALIDITY_SECONDS,
        tz=timezone.utc
    )

    # Check for existing pairing
    existing = None
    for p in pairings.values():
        if p['hermes_id'] == hermes_id:
            existing = p
            break

    if existing:
        # Refresh token (idempotent re-pair)
        token = str(uuid.uuid4())
        existing['token'] = token
        existing['token_expires_at'] = expires.isoformat()
        _save_hermes_pairings(pairings)

        # Append pairing event
        spine.append_pairing_requested(
            device_name,
            HERMES_CAPABILITIES,
            principal.id
        )
        spine.append_pairing_granted(
            device_name,
            HERMES_CAPABILITIES,
            principal.id
        )

        return HermesPairing(**existing)

    # Create new pairing
    pairing = HermesPairing(
        id=str(uuid.uuid4()),
        hermes_id=hermes_id,
        principal_id=principal.id,
        device_name=device_name,
        capabilities=HERMES_CAPABILITIES,
        paired_at=now.isoformat(),
        token=str(uuid.uuid4()),
        token_expires_at=expires.isoformat()
    )

    pairings[pairing.id] = asdict(pairing)
    _save_hermes_pairings(pairings)

    # Append pairing events
    spine.append_pairing_requested(
        device_name,
        HERMES_CAPABILITIES,
        principal.id
    )
    spine.append_pairing_granted(
        device_name,
        HERMES_CAPABILITIES,
        principal.id
    )

    return pairing


def get_hermes_pairing(hermes_id: str) -> Optional[HermesPairing]:
    """Get a Hermes pairing record by hermes_id."""
    pairings = _load_hermes_pairings()
    for p in pairings.values():
        if p['hermes_id'] == hermes_id:
            return HermesPairing(**p)
    return None


def issue_authority_token(hermes_id: str) -> str:
    """
    Issue a new authority token for a paired Hermes.

    Returns a base64-encoded JSON token with observe + summarize capabilities.
    """
    pairing = get_hermes_pairing(hermes_id)
    if not pairing:
        raise ValueError(f"HERMES_NOT_PAIRED: '{hermes_id}' is not paired")

    if is_token_expired(pairing.token_expires_at):
        raise ValueError("HERMES_TOKEN_EXPIRED: pairing token has expired")

    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + TOKEN_VALIDITY_SECONDS,
        tz=timezone.utc
    )

    import base64
    payload = {
        "hermes_id": hermes_id,
        "principal_id": pairing.principal_id,
        "capabilities": HERMES_CAPABILITIES,
        "issued_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }

    token_bytes = json.dumps(payload).encode()
    token = base64.b64encode(token_bytes).decode()

    # Record token issuance
    _save_authority_token({
        "hermes_id": hermes_id,
        "issued_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "token_preview": token[:8] + "..."
    })

    return token


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and establish a Hermes connection.

    Raises ValueError if:
    - Token is invalid or malformed
    - Token has expired
    - Token requests a capability Hermes cannot have (e.g., 'control')
    - hermes_id is not paired
    """
    token = decode_authority_token(authority_token)

    # Verify hermes_id is paired
    pairing = get_hermes_pairing(token.hermes_id)
    if not pairing:
        raise ValueError(f"HERMES_NOT_PAIRED: '{token.hermes_id}' has not been paired")

    # Verify principal matches
    if token.principal_id != pairing.principal_id:
        raise ValueError("HERMES_INVALID_TOKEN: principal_id mismatch")

    # Verify capabilities are subset of HERMES_CAPABILITIES
    for cap in token.capabilities:
        if cap not in HERMES_CAPABILITIES:
            raise ValueError(
                f"HERMES_INVALID_CAPABILITY: Hermes cannot request '{cap}' capability"
            )

    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + TOKEN_VALIDITY_SECONDS,
        tz=timezone.utc
    )

    return HermesConnection(
        hermes_id=token.hermes_id,
        principal_id=token.principal_id,
        capabilities=token.capabilities,
        connected_at=now.isoformat(),
        token_expires_at=token.expires_at
    )


# ---------------------------------------------------------------------------
# Adapter operations
# ---------------------------------------------------------------------------

def read_status(connection: HermesConnection) -> dict:
    """
    Read current miner status through the adapter.

    Requires 'observe' capability. Returns a miner snapshot with
    status, mode, hashrate, temperature, uptime, and freshness.

    Raises PermissionError if connection lacks observe capability.
    """
    if 'observe' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: observe capability required to read status"
        )

    # Import here to avoid circular imports at module level
    from daemon import miner

    snapshot = miner.get_snapshot()

    # Strip any fields Hermes shouldn't see
    return {
        "status": snapshot.get("status"),
        "mode": snapshot.get("mode"),
        "hashrate_hs": snapshot.get("hashrate_hs"),
        "temperature": snapshot.get("temperature"),
        "uptime_seconds": snapshot.get("uptime_seconds"),
        "freshness": snapshot.get("freshness"),
        "source": "hermes_adapter",
        "hermes_id": connection.hermes_id
    }


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: Optional[list[str]] = None
) -> dict:
    """
    Append a Hermes summary to the event spine.

    Requires 'summarize' capability. The summary is written as a
    hermes_summary event with the given text and authority scope.

    Raises PermissionError if connection lacks summarize capability.
    """
    if 'summarize' not in connection.capabilities:
        raise PermissionError(
            "HERMES_UNAUTHORIZED: summarize capability required to append summary"
        )

    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID_SUMMARY: summary_text cannot be empty")

    scope = authority_scope or connection.capabilities

    event = spine.append_hermes_summary(
        summary_text=summary_text.strip(),
        authority_scope=scope,
        principal_id=connection.principal_id
    )

    return {
        "appended": True,
        "event_id": event.id,
        "kind": event.kind,
        "created_at": event.created_at
    }


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]:
    """
    Return events Hermes is allowed to see, filtered to HERMES_READABLE_EVENTS.

    This blocks user_message events. Hermes can see:
    - hermes_summary (its own summaries)
    - miner_alert (alerts it may have generated)
    - control_receipt (to understand recent actions)

    Hermes cannot see:
    - user_message (private communications)
    """
    # Over-fetch to account for filtering
    all_events = spine.get_events(limit=limit * 3)

    filtered = []
    for event in all_events:
        if event.kind in HERMES_EVENT_KINDS:
            filtered.append({
                "id": event.id,
                "principal_id": event.principal_id,
                "kind": event.kind,
                "payload": event.payload,
                "created_at": event.created_at
            })

        if len(filtered) >= limit:
            break

    return filtered


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Hermes Adapter Smoke Test")
    print("=" * 40)
    print(f"Capabilities: {HERMES_CAPABILITIES}")
    print(f"Readable events: {HERMES_EVENT_KINDS}")

    # Test: pair Hermes
    print("\nPairing hermes-001...")
    pairing = pair_hermes("hermes-001", "hermes-agent")
    print(f"  Pairing ID: {pairing.id}")
    print(f"  Hermes ID: {pairing.hermes_id}")
    print(f"  Capabilities: {pairing.capabilities}")

    # Test: issue token
    print("\nIssuing authority token...")
    token = issue_authority_token("hermes-001")
    print(f"  Token (preview): {token[:20]}...")

    # Test: connect with token
    print("\nConnecting with authority token...")
    conn = connect(token)
    print(f"  Connected: {conn.hermes_id}")
    print(f"  Capabilities: {conn.capabilities}")

    # Test: read status
    print("\nReading miner status (observe)...")
    status = read_status(conn)
    print(f"  Status: {status.get('status')}")
    print(f"  Mode: {status.get('mode')}")
    print(f"  Hashrate: {status.get('hashrate_hs')} H/s")

    # Test: append summary
    print("\nAppending summary (summarize)...")
    result = append_summary(
        conn,
        "Miner running normally at 50kH/s",
        authority_scope=['observe']
    )
    print(f"  Appended: {result.get('appended')}")
    print(f"  Event ID: {result.get('event_id')}")

    # Test: get filtered events
    print("\nReading filtered events...")
    events = get_filtered_events(conn, limit=5)
    print(f"  Events returned: {len(events)}")
    for e in events:
        print(f"    - {e['kind']}: {e['created_at']}")

    print("\n✓ All smoke tests passed")
