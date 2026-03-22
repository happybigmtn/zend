#!/usr/bin/env python3
"""
Zend Home Miner CLI

Command-line interface for the home-miner daemon.
Provides pairing, status, control, and Hermes commands.
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
import hermes

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


def daemon_call_raw(method: str, path: str, data: dict = None, headers: dict = None) -> dict:
    """Make a call to the daemon with optional custom headers."""
    url = f"{DAEMON_URL}{path}"

    try:
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)

        if method == 'GET':
            req = urllib.request.Request(url, headers=req_headers)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data or {}).encode(),
                headers=req_headers
            )
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
    if not has_capability(args.client, 'control'):
        print(json.dumps({
            "success": False,
            "error": "unauthorized",
            "message": "This device lacks 'control' capability"
        }, indent=2))
        return 1

    principal = load_or_create_principal()

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


# -------------------------------------------------------------------------
# Hermes commands
# -------------------------------------------------------------------------

def _resolve_token(hermes_id: str, token: str = None) -> str:
    """Resolve token from argument or state file."""
    if token:
        return token
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "state")
    )
    token_file = os.path.join(state_dir, f"hermes_token_{hermes_id}.json")
    if os.path.exists(token_file):
        with open(token_file) as f:
            data = json.load(f)
            return data["authority_token"]
    return None


def cmd_hermes_pair(args):
    """Pair a new Hermes agent and issue an authority token."""
    principal = load_or_create_principal()

    record = hermes.pair_hermes(
        hermes_id=args.hermes_id,
        device_name=args.device_name,
        principal_id=principal.id,
    )

    token_encoded, token_obj = hermes.issue_hermes_token(
        hermes_id=args.hermes_id,
        principal_id=principal.id,
        capabilities=hermes.HERMES_CAPABILITIES,
        ttl_hours=args.ttl_hours,
    )

    # Persist token to state so future commands can find it
    state_dir = os.environ.get(
        "ZEND_STATE_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "state")
    )
    os.makedirs(state_dir, exist_ok=True)
    token_file = os.path.join(state_dir, f"hermes_token_{args.hermes_id}.json")
    with open(token_file, "w") as f:
        json.dump({
            "authority_token": token_encoded,
            "expires_at": token_obj.expires_at,
            "hermes_id": args.hermes_id,
            "principal_id": principal.id,
        }, f, indent=2)

    print(json.dumps({
        "hermes_id": record["hermes_id"],
        "device_name": record["device_name"],
        "principal_id": record["principal_id"],
        "capabilities": record["capabilities"],
        "paired_at": record["paired_at"],
        "authority_token": token_encoded,
        "expires_at": token_obj.expires_at,
    }, indent=2))

    return 0


def cmd_hermes_connect(args):
    """Connect to the daemon as a Hermes agent."""
    token = _resolve_token(args.hermes_id, args.token)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": "Provide --token or run: zend hermes pair --hermes-id <id> first"
        }, indent=2))
        return 1

    result = daemon_call('POST', '/hermes/connect', {"authority_token": token})
    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


def cmd_hermes_status(args):
    """Read miner status through the Hermes adapter."""
    token = _resolve_token(args.hermes_id, args.token)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": "Provide --token or pair first with: zend hermes pair"
        }, indent=2))
        return 1

    result = daemon_call('POST', '/hermes/connect', {"authority_token": token})
    if "error" in result:
        print(json.dumps(result, indent=2))
        return 1

    status_result = daemon_call_raw(
        'GET',
        '/hermes/status',
        headers={"Authorization": f"Hermes {token}"},
    )
    print(json.dumps(status_result, indent=2))
    return 0 if "error" not in status_result else 1


def cmd_hermes_summary(args):
    """Append a Hermes summary to the event spine."""
    token = _resolve_token(args.hermes_id, args.token)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": "Provide --token or pair first with: zend hermes pair"
        }, indent=2))
        return 1

    result = daemon_call('POST', '/hermes/connect', {"authority_token": token})
    if "error" in result:
        print(json.dumps(result, indent=2))
        return 1

    append_result = daemon_call_raw(
        'POST',
        '/hermes/summary',
        {"summary_text": args.text, "authority_scope": args.scope},
        headers={"Authorization": f"Hermes {token}"},
    )
    print(json.dumps(append_result, indent=2))
    return 0 if "error" not in append_result else 1


def cmd_hermes_events(args):
    """Read filtered events through the Hermes adapter (no user_message)."""
    token = _resolve_token(args.hermes_id, args.token)
    if not token:
        print(json.dumps({
            "error": "no_token",
            "message": "Provide --token or pair first with: zend hermes pair"
        }, indent=2))
        return 1

    result = daemon_call('POST', '/hermes/connect', {"authority_token": token})
    if "error" in result:
        print(json.dumps(result, indent=2))
        return 1

    events_result = daemon_call_raw(
        'GET',
        '/hermes/events',
        headers={"Authorization": f"Hermes {token}"},
    )

    if "error" in events_result:
        print(json.dumps(events_result, indent=2))
        return 1

    events = events_result.get("events", [])
    print(f"# {len(events)} events (user_message filtered)")
    for event in events:
        print(json.dumps(event, indent=2))

    return 0


# -------------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------------

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

    # Hermes subcommand group
    hermes_parser = subparsers.add_parser('hermes', help='Hermes AI agent commands')
    hermes_subparsers = hermes_parser.add_subparsers(dest='hermes_command')

    hermes_pair = hermes_subparsers.add_parser('pair', help='Pair a Hermes agent')
    hermes_pair.add_argument('--hermes-id', required=True, help='Hermes instance ID')
    hermes_pair.add_argument('--device-name', default='hermes-agent',
                              help='Human-readable name')
    hermes_pair.add_argument('--ttl-hours', type=int, default=24,
                              help='Token TTL in hours (default: 24)')

    hermes_connect = hermes_subparsers.add_parser('connect', help='Connect as Hermes')
    hermes_connect.add_argument('--hermes-id', required=True, help='Hermes instance ID')
    hermes_connect.add_argument('--token', help='Authority token (or auto-loaded from state)')

    hermes_status = hermes_subparsers.add_parser('status', help='Read status via Hermes adapter')
    hermes_status.add_argument('--hermes-id', required=True, help='Hermes instance ID')
    hermes_status.add_argument('--token', help='Authority token (or auto-loaded from state)')

    hermes_summary = hermes_subparsers.add_parser('summary', help='Append Hermes summary')
    hermes_summary.add_argument('--hermes-id', required=True, help='Hermes instance ID')
    hermes_summary.add_argument('--token', help='Authority token (or auto-loaded from state)')
    hermes_summary.add_argument('--text', required=True, help='Summary text')
    hermes_summary.add_argument('--scope', default='observe',
                                 help='Authority scope (default: observe)')

    hermes_events = hermes_subparsers.add_parser('events', help='Read filtered events')
    hermes_events.add_argument('--hermes-id', required=True, help='Hermes instance ID')
    hermes_events.add_argument('--token', help='Authority token (or auto-loaded from state)')

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

    # Hermes commands
    elif args.command == 'hermes':
        if not args.hermes_command:
            hermes_parser.print_help()
            return 1
        elif args.hermes_command == 'pair':
            return cmd_hermes_pair(args)
        elif args.hermes_command == 'connect':
            return cmd_hermes_connect(args)
        elif args.hermes_command == 'status':
            return cmd_hermes_status(args)
        elif args.hermes_command == 'summary':
            return cmd_hermes_summary(args)
        elif args.hermes_command == 'events':
            return cmd_hermes_events(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
