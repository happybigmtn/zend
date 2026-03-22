#!/usr/bin/env python3
"""
Zend Home Miner CLI

Command-line interface for the home-miner daemon.
Provides pairing, status, control commands, and Hermes agent commands.
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


# Hermes subcommands
def cmd_hermes(args):
    """Dispatch Hermes subcommands."""
    if args.hermes_command == 'pair':
        return cmd_hermes_pair(args)
    elif args.hermes_command == 'connect':
        return cmd_hermes_connect(args)
    elif args.hermes_command == 'status':
        return cmd_hermes_status(args)
    elif args.hermes_command == 'summary':
        return cmd_hermes_summary(args)
    elif args.hermes_command == 'events':
        return cmd_hermes_events(args)
    elif args.hermes_command == 'token':
        return cmd_hermes_token(args)
    return 1


def cmd_hermes_pair(args):
    """Pair a new Hermes agent."""
    result = daemon_call('POST', '/hermes/pair', {
        'hermes_id': args.hermes_id,
        'device_name': args.device_name or f'hermes-{args.hermes_id}'
    })
    
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    
    print(json.dumps({
        "success": True,
        "hermes_id": result['hermes_id'],
        "capabilities": result['capabilities'],
        "paired_at": result['paired_at'],
        "token": result['token']
    }, indent=2))
    
    # Store token locally for convenience
    if args.save_token:
        token_file = os.path.expanduser('~/.zend-hermes-token')
        with open(token_file, 'w') as f:
            f.write(result['token'])
        print(f"Token saved to {token_file}")
    
    return 0


def cmd_hermes_connect(args):
    """Connect Hermes with authority token."""
    # Get token from file or argument
    token = args.token
    if args.token_file:
        with open(os.path.expanduser(args.token_file), 'r') as f:
            token = f.read().strip()
    elif not token:
        # Try default token file
        token_file = os.path.expanduser('~/.zend-hermes-token')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token = f.read().strip()
    
    if not token:
        print(json.dumps({
            "error": "missing_token",
            "message": "Provide --token or --token-file, or save token with 'hermes pair --save-token'"
        }, indent=2))
        return 1
    
    result = daemon_call('POST', '/hermes/connect', {
        'authority_token': token
    })
    
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    
    print(json.dumps({
        "connected": True,
        "hermes_id": result['hermes_id'],
        "capabilities": result['capabilities'],
        "connected_at": result['connected_at'],
        "authority_scope": result['authority_scope']
    }, indent=2))
    return 0


def cmd_hermes_status(args):
    """Read miner status through Hermes adapter."""
    if not args.hermes_id:
        print(json.dumps({
            "error": "missing_hermes_id",
            "message": "Provide --hermes-id or connect first with 'hermes connect'"
        }, indent=2))
        return 1
    
    result = daemon_call('GET', '/hermes/status', headers={
        'Authorization': f'Hermes {args.hermes_id}'
    })
    
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    
    print(json.dumps(result, indent=2))
    return 0


def cmd_hermes_summary(args):
    """Append a Hermes summary."""
    if not args.hermes_id:
        print(json.dumps({
            "error": "missing_hermes_id",
            "message": "Provide --hermes-id"
        }, indent=2))
        return 1
    
    if not args.text:
        print(json.dumps({
            "error": "missing_summary_text",
            "message": "Provide --text for the summary"
        }, indent=2))
        return 1
    
    result = daemon_call('POST', '/hermes/summary', {
        'summary_text': args.text,
        'authority_scope': args.scope or 'observe'
    }, headers={
        'Authorization': f'Hermes {args.hermes_id}'
    })
    
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    
    print(json.dumps({
        "success": True,
        "appended": result.get('appended', True),
        "event_id": result.get('event_id')
    }, indent=2))
    return 0


def cmd_hermes_events(args):
    """Get filtered events for Hermes."""
    if not args.hermes_id:
        print(json.dumps({
            "error": "missing_hermes_id",
            "message": "Provide --hermes-id or connect first"
        }, indent=2))
        return 1
    
    result = daemon_call('GET', '/hermes/events', headers={
        'Authorization': f'Hermes {args.hermes_id}'
    })
    
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    
    events = result.get('events', [])
    print(f"Found {len(events)} events (user_message events filtered):")
    for event in events:
        print(json.dumps({
            "id": event['id'],
            "kind": event['kind'],
            "payload": event['payload'],
            "created_at": event['created_at']
        }, indent=2))
    
    return 0


def cmd_hermes_token(args):
    """Generate an authority token locally (for testing)."""
    principal = load_or_create_principal()
    
    # Get or prompt for hermes_id
    hermes_id = args.hermes_id
    if not hermes_id:
        hermes_id = input("Enter Hermes ID: ").strip()
    
    capabilities = args.capabilities.split(',') if args.capabilities else ['observe', 'summarize']
    expires_hours = args.expires or 24
    
    token = hermes.create_authority_token(hermes_id, capabilities, expires_hours)
    
    print(json.dumps({
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": capabilities,
        "expires_hours": expires_hours,
        "authority_token": token
    }, indent=2))
    
    if args.save:
        token_file = os.path.expanduser('~/.zend-hermes-token')
        with open(token_file, 'w') as f:
            f.write(token)
        print(f"Token saved to {token_file}")
    
    return 0


def daemon_call(method: str, path: str, data: dict = None, headers: dict = None) -> dict:
    """Make a call to the daemon with optional custom headers."""
    url = f"{DAEMON_URL}{path}"
    
    header_dict = {'Content-Type': 'application/json'}
    if headers:
        header_dict.update(headers)

    try:
        if method == 'GET':
            req = urllib.request.Request(url, headers=header_dict)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data or {}).encode(),
                headers=header_dict
            )
            req.get_method = lambda: method

        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    except urllib.error.URLError as e:
        return {"error": "daemon_unavailable", "details": str(e)}


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

    # Hermes subcommand
    hermes = subparsers.add_parser('hermes', help='Hermes AI agent commands')
    hermes_subparsers = hermes.add_subparsers(dest='hermes_command', help='Hermes subcommands')
    
    # Hermes pair
    hermes_pair = hermes_subparsers.add_parser('pair', help='Pair a new Hermes agent')
    hermes_pair.add_argument('--hermes-id', required=True, help='Hermes device ID')
    hermes_pair.add_argument('--device-name', help='Device name (default: hermes-{hermes_id})')
    hermes_pair.add_argument('--save-token', action='store_true', help='Save token to ~/.zend-hermes-token')
    
    # Hermes connect
    hermes_connect = hermes_subparsers.add_parser('connect', help='Connect Hermes with authority token')
    hermes_connect.add_argument('--token', help='Authority token string')
    hermes_connect.add_argument('--token-file', help='File containing authority token')
    
    # Hermes status
    hermes_status = hermes_subparsers.add_parser('status', help='Read miner status through adapter')
    hermes_status.add_argument('--hermes-id', help='Hermes ID (required if not connected)')
    
    # Hermes summary
    hermes_summary = hermes_subparsers.add_parser('summary', help='Append a Hermes summary')
    hermes_summary.add_argument('--hermes-id', required=True, help='Hermes ID')
    hermes_summary.add_argument('--text', required=True, help='Summary text')
    hermes_summary.add_argument('--scope', help='Authority scope (default: observe)')
    
    # Hermes events
    hermes_events = hermes_subparsers.add_parser('events', help='Get filtered events')
    hermes_events.add_argument('--hermes-id', help='Hermes ID (required if not connected)')
    
    # Hermes token (local token generation)
    hermes_token = hermes_subparsers.add_parser('token', help='Generate authority token locally')
    hermes_token.add_argument('--hermes-id', help='Hermes ID')
    hermes_token.add_argument('--capabilities', default='observe,summarize', help='Comma-separated capabilities')
    hermes_token.add_argument('--expires', type=int, default=24, help='Token validity in hours')
    hermes_token.add_argument('--save', action='store_true', help='Save token to ~/.zend-hermes-token')

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


if __name__ == '__main__':
    sys.exit(main())
