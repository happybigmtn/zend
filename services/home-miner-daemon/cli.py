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
    pairing = get_pairing_by_device(args.device)

    if pairing is None:
        pairing = pair_client(args.device, ['observe'])

        # Append pairing granted event only for newly-created bootstrap state.
        spine.append_pairing_granted(
            pairing.device_name,
            pairing.capabilities,
            principal.id
        )

    if pairing.principal_id != principal.id:
        print(json.dumps({
            "error": "invalid_principal",
            "message": "Existing bootstrap pairing belongs to a different principal"
        }, indent=2))
        return 1

    print(json.dumps({
        "principal_id": principal.id,
        "device_name": pairing.device_name,
        "pairing_id": pairing.id,
        "capabilities": pairing.capabilities,
        "paired_at": pairing.paired_at
    }, indent=2))

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
    surface = args.surface if args.surface != 'all' else None
    events = spine.get_events(kind=kind, limit=args.limit, surface=surface)

    for event in events:
        print(json.dumps(spine.serialize_event(event), indent=2))

    return 0


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
    events.add_argument(
        '--kind',
        choices=['all'] + [kind.value for kind in spine.EventKind],
        default='all',
        help='Event kind to filter',
    )
    events.add_argument(
        '--surface',
        choices=['all'] + sorted(spine.SURFACE_ROUTES.keys()),
        default='all',
        help='Projection surface to render',
    )
    events.add_argument('--limit', type=int, default=10, help='Max events to show')

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

    return 0


if __name__ == '__main__':
    sys.exit(main())
