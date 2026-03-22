#!/usr/bin/env python3
"""
Zend Home Miner CLI

Command-line interface for the home-miner daemon.
Provides pairing, status, control, and Hermes agent commands.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Add service to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import load_or_create_principal, pair_client, get_pairing_by_device, has_capability
import spine
import hermes as hermes_adapter

# Default daemon URL
DAEMON_URL = os.environ.get('ZEND_DAEMON_URL', 'http://127.0.0.1:8080')


def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make a call to the daemon."""
    url = f"{DAEMON_URL}{path}"

    try:
        if method == 'GET':
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(url, data=json.dumps(data or {}).encode(),
                                         headers={'Content-Type': 'application/json'})
            req.get_method = lambda: method

        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    except urllib.error.URLError as e:
        return {"error": "daemon_unavailable", "details": str(e)}


def cmd_status(args):
    """Get miner status."""
    if args.client and not (
        has_capability(args.client, 'observe') or has_capability(args.client, 'control')
    ):
        print(json.dumps({
            "error": "unauthorized",
            "message": "This device lacks 'observe' capability"
        }, indent=2))
        return 1

    result = daemon_call('GET', '/status')

    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0


def cmd_health(args):
    """Get daemon health."""
    result = daemon_call('GET', '/health')
    print(json.dumps(result, indent=2))
    return 0


def cmd_bootstrap(args):
    """Bootstrap the daemon and create principal."""
    principal = load_or_create_principal()

    # Generate a pairing token
    pairing = pair_client(args.device, ['observe'])

    print(json.dumps({
        "principal_id": principal.id,
        "device_name": pairing.device_name,
        "pairing_id": pairing.id,
        "capabilities": pairing.capabilities,
        "paired_at": pairing.paired_at
    }, indent=2))

    # Append pairing granted event
    spine.append_pairing_granted(
        pairing.device_name,
        pairing.capabilities,
        principal.id
    )

    return 0


def cmd_pair(args):
    """Pair a new gateway client."""
    principal = load_or_create_principal()

    try:
        pairing = pair_client(args.device, args.capabilities.split(','))

        # Append pairing events
        spine.append_pairing_requested(
            args.device,
            args.capabilities.split(','),
            principal.id
        )
        spine.append_pairing_granted(
            args.device,
            pairing.capabilities,
            principal.id
        )

        print(json.dumps({
            "success": True,
            "device_name": pairing.device_name,
            "capabilities": pairing.capabilities,
            "paired_at": pairing.paired_at
        }, indent=2))

        return 0

    except ValueError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1


def cmd_control(args):
    """Control the miner (start/stop/set_mode)."""
    # Check capability
    if not has_capability(args.client, 'control'):
        print(json.dumps({
            "success": False,
            "error": "unauthorized",
            "message": "This device lacks 'control' capability"
        }, indent=2))
        return 1

    principal = load_or_create_principal()
    pairing = get_pairing_by_device(args.client)

    if args.action == 'start':
        result = daemon_call('POST', '/miner/start')
    elif args.action == 'stop':
        result = daemon_call('POST', '/miner/stop')
    elif args.action == 'set_mode':
        result = daemon_call('POST', '/miner/set_mode', {'mode': args.mode})
    else:
        print(json.dumps({"success": False, "error": "invalid_action"}))
        return 1

    # Append control receipt
    status = 'accepted' if result.get('success') else 'rejected'
    spine.append_control_receipt(
        args.action,
        args.mode if args.action == 'set_mode' else None,
        status,
        principal.id
    )

    if result.get('success'):
        print(json.dumps({
            "success": True,
            "acknowledged": True,
            "message": f"Miner {args.action} accepted by home miner (not client device)"
        }, indent=2))
    else:
        print(json.dumps({
            "success": False,
            "error": result.get('error', 'unknown')
        }, indent=2))

    return 0 if result.get('success') else 1


def cmd_events(args):
    """List events from the spine."""
    if args.client and not (
        has_capability(args.client, 'observe') or has_capability(args.client, 'control')
    ):
        print(json.dumps({
            "error": "unauthorized",
            "message": "This device lacks 'observe' capability"
        }, indent=2))
        return 1

    kind = args.kind if args.kind != 'all' else None
    events = spine.get_events(kind=kind, limit=args.limit)

    for event in events:
        print(json.dumps({
            "id": event.id,
            "kind": event.kind,
            "payload": event.payload,
            "created_at": event.created_at
        }, indent=2))

    return 0


def cmd_hermes_pair(args):
    """Pair a Hermes agent with the daemon.

    Creates a Hermes pairing record and issues an authority token.
    The token is printed to stdout — save it for the connect command.
    """
    principal = load_or_create_principal()

    result = daemon_call('POST', '/hermes/pair', {
        "hermes_id": args.hermes_id,
        "device_name": args.device_name or args.hermes_id,
    })

    if 'error' in result and not result.get('paired'):
        print(json.dumps(result, indent=2))
        return 1

    # Pretty-print the token for easy copying
    print(json.dumps({
        "status": "paired",
        "hermes_id": result.get('hermes_id'),
        "device_name": result.get('device_name'),
        "capabilities": result.get('capabilities'),
        "paired_at": result.get('paired_at'),
        "token": result.get('token'),
        "token_expires_at": result.get('token_expires_at'),
    }, indent=2))

    return 0


def cmd_hermes_connect(args):
    """Connect Hermes and read miner status.

    Requires --token (from hermes pair command).
    Displays connection state and current miner status.
    """
    # Store token locally for subsequent commands
    if args.token:
        _save_hermes_token(args.hermes_id, args.token)

    result = daemon_call('POST', '/hermes/connect', {"token": args.token})

    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1

    print(json.dumps({
        "connected": True,
        "hermes_id": result.get('hermes_id'),
        "principal_id": result.get('principal_id'),
        "capabilities": result.get('capabilities'),
        "connected_at": result.get('connected_at'),
        "token_expires_at": result.get('token_expires_at'),
    }, indent=2))

    # If --status flag, also fetch status
    if args.status:
        status_result = _hermes_auth_call(args.hermes_id, 'GET', '/hermes/status')
        if status_result:
            print(json.dumps({"miner_status": status_result.get('status')}, indent=2))

    return 0


def cmd_hermes_summary(args):
    """Append a Hermes summary to the event spine.

    Requires --token (from hermes pair command) and --text for the summary.
    """
    token = args.token or _load_hermes_token(args.hermes_id)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": f"No stored token for {args.hermes_id}. Run 'hermes pair' first or pass --token."
        }, indent=2))
        return 1

    result = daemon_call('POST', '/hermes/summary', {
        "token": token,
        "summary_text": args.text,
        "authority_scope": args.scope or 'observe',
    })

    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1

    print(json.dumps({
        "appended": True,
        "event_id": result.get('event_id'),
        "kind": result.get('kind'),
        "created_at": result.get('created_at'),
    }, indent=2))

    return 0


def cmd_hermes_events(args):
    """Read Hermes-filtered events from the event spine.

    Shows hermes_summary, miner_alert, and control_receipt events.
    Does NOT show user_message events.
    """
    token = args.token or _load_hermes_token(args.hermes_id)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": f"No stored token for {args.hermes_id}. Run 'hermes pair' first or pass --token."
        }, indent=2))
        return 1

    # Use Authorization header with Hermes scheme
    url = f"{DAEMON_URL}/hermes/events"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Hermes {args.hermes_id}')
    # Also include token in header for connection validation
    req.add_header('X-Hermes-Token', token)

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(json.dumps({"error": "daemon_unavailable", "details": str(e)}, indent=2))
        return 1

    print(json.dumps({
        "hermes_id": result.get('hermes_id'),
        "count": result.get('count'),
        "events": result.get('events', []),
    }, indent=2))

    return 0


# ---------------------------------------------------------------------------
# Token storage helpers (per-hermes, in state dir)
# ---------------------------------------------------------------------------

def _hermes_token_path(hermes_id: str) -> str:
    state_dir = os.environ.get('ZEND_STATE_DIR', os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', 'state'
    ))
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f'hermes-token-{hermes_id}.json')


def _save_hermes_token(hermes_id: str, token: str):
    path = _hermes_token_path(hermes_id)
    with open(path, 'w') as f:
        json.dump({"token": token}, f)


def _load_hermes_token(hermes_id: str) -> Optional[str]:
    path = _hermes_token_path(hermes_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f).get('token')
    return None


def _hermes_auth_call(hermes_id: str, method: str, path: str, data: dict = None) -> Optional[dict]:
    """Make an authenticated Hermes API call."""
    token = _load_hermes_token(hermes_id)
    if not token:
        return None

    url = f"{DAEMON_URL}{path}"
    try:
        if method == 'GET':
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data or {}).encode(),
                headers={'Content-Type': 'application/json'}
            )
            req.get_method = lambda: method

        req.add_header('Authorization', f'Hermes {hermes_id}')
        req.add_header('X-Hermes-Token', token)

        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError:
        return None


def main():
    parser = argparse.ArgumentParser(description='Zend Home Miner CLI')
    subparsers = parser.add_subparsers(dest='command')

    # Status command
    status = subparsers.add_parser('status', help='Get miner status')
    status.add_argument('--client', help='Client device name for observe authorization')

    # Health command
    subparsers.add_parser('health', help='Get daemon health')

    # Bootstrap command
    bootstrap = subparsers.add_parser('bootstrap', help='Bootstrap daemon and create principal')
    bootstrap.add_argument('--device', default='alice-phone', help='Device name')

    # Pair command
    pair = subparsers.add_parser('pair', help='Pair a new gateway client')
    pair.add_argument('--device', required=True, help='Device name')
    pair.add_argument('--capabilities', default='observe', help='Comma-separated capabilities')

    # Control command
    control = subparsers.add_parser('control', help='Control miner')
    control.add_argument('--client', required=True, help='Client device name')
    control.add_argument('--action', required=True, choices=['start', 'stop', 'set_mode'],
                        help='Control action')
    control.add_argument('--mode', choices=['paused', 'balanced', 'performance'],
                        help='Mining mode (for set_mode)')

    # Events command
    events = subparsers.add_parser('events', help='List events from spine')
    events.add_argument('--client', help='Client device name for observe authorization')
    events.add_argument('--kind', default='all', help='Event kind to filter')
    events.add_argument('--limit', type=int, default=10, help='Max events to show')

    # Hermes command group
    hermes = subparsers.add_parser('hermes', help='Hermes agent commands')
    hermes_subparsers = hermes.add_subparsers(dest='hermes_command')

    # hermes pair
    hermes_pair = hermes_subparsers.add_parser('pair', help='Pair a Hermes agent')
    hermes_pair.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hermes_pair.add_argument('--device-name', help='Human-readable device name (default: hermes-id)')

    # hermes connect
    hermes_connect = hermes_subparsers.add_parser('connect', help='Connect Hermes to daemon')
    hermes_connect.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hermes_connect.add_argument('--token', help='Authority token (from hermes pair)')
    hermes_connect.add_argument('--status', action='store_true', help='Also fetch miner status')

    # hermes summary
    hermes_summary = hermes_subparsers.add_parser('summary', help='Append a Hermes summary')
    hermes_summary.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hermes_summary.add_argument('--token', help='Authority token (from hermes pair)')
    hermes_summary.add_argument('--text', required=True, help='Summary text to append')
    hermes_summary.add_argument('--scope', default='observe', help='Authority scope')

    # hermes events
    hermes_events = hermes_subparsers.add_parser('events', help='Read filtered events')
    hermes_events.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hermes_events.add_argument('--token', help='Authority token (from hermes pair)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'status':
        return cmd_status(args)
    elif args.command == 'health':
        return cmd_health(args)
    elif args.command == 'bootstrap':
        return cmd_bootstrap(args)
    elif args.command == 'pair':
        return cmd_pair(args)
    elif args.command == 'control':
        return cmd_control(args)
    elif args.command == 'events':
        return cmd_events(args)
    elif args.command == 'hermes':
        return cmd_hermes(args)

    return 0


def cmd_hermes(args):
    """Dispatch Hermes subcommands."""
    sub = args.hermes_command
    if sub == 'pair':
        return cmd_hermes_pair(args)
    elif sub == 'connect':
        return cmd_hermes_connect(args)
    elif sub == 'summary':
        return cmd_hermes_summary(args)
    elif sub == 'events':
        return cmd_hermes_events(args)
    else:
        print("Usage: zend hermes [pair|connect|summary|events]")
        return 1


if __name__ == '__main__':
    sys.exit(main())
