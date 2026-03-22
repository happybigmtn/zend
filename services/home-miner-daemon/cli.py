#!/usr/bin/env python3
"""
Zend Home Miner CLI

Command-line interface for the home-miner daemon.
Provides pairing, status, and control commands.
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


def daemon_call(method: str, path: str, data: dict = None, headers: dict = None) -> dict:
    """Make a call to the daemon."""
    url = f"{DAEMON_URL}{path}"
    headers = dict(headers or {})

    try:
        if method == 'GET':
            req = urllib.request.Request(url, headers=headers)
        else:
            headers.setdefault('Content-Type', 'application/json')
            req = urllib.request.Request(url, data=json.dumps(data or {}).encode(),
                                         headers=headers)
            req.get_method = lambda: method

        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            return body
        except Exception:
            return {"error": f"HTTP_{e.code}", "details": str(e)}
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
    """Pair a Hermes agent with observe + summarize capabilities."""
    record = hermes.pair_hermes(args.hermes_id, args.device_name)
    print(json.dumps({
        "success": True,
        "hermes_id": record['hermes_id'],
        "device_name": record['device_name'],
        "principal_id": record['principal_id'],
        "capabilities": record['capabilities'],
        "paired_at": record['paired_at'],
        "token_expires_at": record['token_expires_at'],
    }, indent=2))
    return 0


def cmd_hermes_connect(args):
    """Connect Hermes using an authority token or pairing record."""
    if args.token:
        result = daemon_call('POST', '/hermes/connect', {'authority_token': args.token})
    else:
        hermes_id = args.hermes_id
        result = daemon_call('POST', '/hermes/pair', {
            'hermes_id': hermes_id,
            'device_name': args.device_name or hermes_id,
        })
        if result.get('paired'):
            # Auto-connect after pairing using the stored pairing record
            result = daemon_call('POST', '/hermes/connect', {'hermes_id': hermes_id})

    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def cmd_hermes_status(args):
    """Read miner status as Hermes (requires Hermes auth)."""
    if not args.hermes_id:
        print(json.dumps({"error": "hermes_id required"}, indent=2))
        return 1
    auth = {'Authorization': f'Hermes {args.hermes_id}'}
    result = daemon_call('GET', '/hermes/status', headers=auth)
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def cmd_hermes_summary(args):
    """Append a Hermes summary to the event spine."""
    if not args.hermes_id:
        print(json.dumps({"error": "hermes_id required"}, indent=2))
        return 1
    if not args.text:
        print(json.dumps({"error": "summary text required (--text)"}, indent=2))
        return 1
    auth = {'Authorization': f'Hermes {args.hermes_id}'}
    result = daemon_call('POST', '/hermes/summary', {
        'summary_text': args.text,
        'authority_scope': args.scope.split(',') if args.scope else ['summarize'],
    }, headers=auth)
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


def cmd_hermes_events(args):
    """Read Hermes-filtered events from the spine."""
    if not args.hermes_id:
        print(json.dumps({"error": "hermes_id required"}, indent=2))
        return 1
    auth = {'Authorization': f'Hermes {args.hermes_id}'}
    result = daemon_call('GET', '/hermes/events', headers=auth)
    if 'error' in result:
        print(json.dumps(result, indent=2))
        return 1
    for event in result.get('events', []):
        print(json.dumps(event, indent=2))
    return 0


def _cmd_hermes(args):
    """Dispatch to Hermes subcommand."""
    sub = args.hermes_command
    if sub == 'pair':
        return cmd_hermes_pair(args)
    elif sub == 'connect':
        return cmd_hermes_connect(args)
    elif sub == 'status':
        return cmd_hermes_status(args)
    elif sub == 'summary':
        return cmd_hermes_summary(args)
    elif sub == 'events':
        return cmd_hermes_events(args)
    return 1


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
    hermes_parser = subparsers.add_parser('hermes', help='Hermes adapter commands')
    hermes_subparsers = hermes_parser.add_subparsers(dest='hermes_command', required=True)

    # hermes pair
    hp = hermes_subparsers.add_parser('pair', help='Pair a Hermes agent (observe + summarize)')
    hp.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hp.add_argument('--device-name', help='Device name (defaults to hermes-id)')

    # hermes connect
    hc = hermes_subparsers.add_parser('connect', help='Connect Hermes with authority token')
    hc.add_argument('--token', help='Authority token JSON string')
    hc.add_argument('--hermes-id', help='Hermes ID (used for pairing if no token)')
    hc.add_argument('--device-name', help='Device name (used for pairing)')

    # hermes status
    hs = hermes_subparsers.add_parser('status', help='Read miner status as Hermes')
    hs.add_argument('--hermes-id', required=True, help='Hermes agent identifier')

    # hermes summary
    hsum = hermes_subparsers.add_parser('summary', help='Append Hermes summary to event spine')
    hsum.add_argument('--hermes-id', required=True, help='Hermes agent identifier')
    hsum.add_argument('--text', required=True, help='Summary text')
    hsum.add_argument('--scope', help='Authority scope (comma-separated, default: summarize)')

    # hermes events
    he = hermes_subparsers.add_parser('events', help='Read Hermes-filtered events from spine')
    he.add_argument('--hermes-id', required=True, help='Hermes agent identifier')

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
        return _cmd_hermes(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
