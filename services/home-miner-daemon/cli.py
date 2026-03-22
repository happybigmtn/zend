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
from hermes import (
    pair_hermes,
    get_hermes_pairing,
    generate_authority_token,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events,
    HermesConnection,
)
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
    """Pair a Hermes agent."""
    try:
        caps = args.capabilities.split(',') if args.capabilities else None
        pairing = pair_hermes(args.hermes_id, args.name, caps)
        token = generate_authority_token(
            pairing.hermes_id,
            pairing.capabilities,
            pairing.token_expires_at,
        )
        
        print(json.dumps({
            "success": True,
            "hermes_id": pairing.hermes_id,
            "device_name": pairing.device_name,
            "capabilities": pairing.capabilities,
            "paired_at": pairing.paired_at,
            "authority_token": token,
        }, indent=2))
        return 0
        
    except ValueError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1


def cmd_hermes_status(args):
    """Get Hermes connection and miner status."""
    pairing = get_hermes_pairing(args.hermes_id)
    if not pairing:
        print(json.dumps({
            "error": "not_paired",
            "message": f"Hermes '{args.hermes_id}' is not paired"
        }, indent=2))
        return 1
    
    # Create connection from pairing
    from datetime import datetime, timezone
    connection = HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=pairing.paired_at,
        token_expires_at=pairing.token_expires_at,
    )
    
    try:
        status = hermes_read_status(connection)
        print(json.dumps({
            "hermes_id": connection.hermes_id,
            "capabilities": connection.capabilities,
            "connected_at": connection.connected_at,
            "miner_status": status,
        }, indent=2))
        return 0
    except PermissionError as e:
        print(json.dumps({"error": "unauthorized", "message": str(e)}, indent=2))
        return 1


def cmd_hermes_summary(args):
    """Append a Hermes summary to the event spine."""
    pairing = get_hermes_pairing(args.hermes_id)
    if not pairing:
        print(json.dumps({
            "error": "not_paired",
            "message": f"Hermes '{args.hermes_id}' is not paired"
        }, indent=2))
        return 1
    
    # Create connection from pairing
    connection = HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=pairing.paired_at,
        token_expires_at=pairing.token_expires_at,
    )
    
    try:
        event = hermes_append_summary(connection, args.text, args.scope or 'observe')
        print(json.dumps({
            "success": True,
            "event_id": event.id,
            "kind": event.kind,
            "created_at": event.created_at,
        }, indent=2))
        return 0
    except PermissionError as e:
        print(json.dumps({"error": "unauthorized", "message": str(e)}, indent=2))
        return 1


def cmd_hermes_events(args):
    """List Hermes-filtered events (excludes user_message)."""
    pairing = get_hermes_pairing(args.hermes_id)
    if not pairing:
        print(json.dumps({
            "error": "not_paired",
            "message": f"Hermes '{args.hermes_id}' is not paired"
        }, indent=2))
        return 1
    
    # Create connection from pairing
    connection = HermesConnection(
        hermes_id=pairing.hermes_id,
        principal_id=pairing.principal_id,
        capabilities=pairing.capabilities,
        connected_at=pairing.paired_at,
        token_expires_at=pairing.token_expires_at,
    )
    
    events = get_filtered_events(connection, limit=args.limit)
    print(json.dumps({
        "hermes_id": connection.hermes_id,
        "events": events,
        "filtered": True,
        "note": "user_message events are not visible to Hermes",
    }, indent=2))
    return 0


def cmd_hermes_list(args):
    """List all paired Hermes agents."""
    from hermes import _get_hermes_pairings
    pairings = _get_hermes_pairings()
    
    if not pairings:
        print(json.dumps({"hermes_agents": [], "count": 0}, indent=2))
        return 0
    
    agents = []
    for p in pairings.values():
        agents.append({
            "hermes_id": p.get('hermes_id'),
            "device_name": p.get('device_name'),
            "capabilities": p.get('capabilities'),
            "paired_at": p.get('paired_at'),
        })
    
    print(json.dumps({"hermes_agents": agents, "count": len(agents)}, indent=2))
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
    events.add_argument('--kind', default='all', help='Event kind to filter')
    events.add_argument('--limit', type=int, default=10, help='Max events to show')

    # Hermes subcommands
    hermes = subparsers.add_parser('hermes', help='Hermes agent commands')
    hermes_sub = hermes.add_subparsers(dest='hermes_command')

    # Hermes pair
    hermes_pair = hermes_sub.add_parser('pair', help='Pair a Hermes agent')
    hermes_pair.add_argument('--hermes-id', required=True, help='Hermes agent ID')
    hermes_pair.add_argument('--name', default=None, help='Device name')
    hermes_pair.add_argument('--capabilities', default=None, help='Comma-separated capabilities (default: observe,summarize)')

    # Hermes status
    hermes_status = hermes_sub.add_parser('status', help='Get Hermes connection and miner status')
    hermes_status.add_argument('--hermes-id', required=True, help='Hermes agent ID')

    # Hermes summary
    hermes_summary = hermes_sub.add_parser('summary', help='Append a Hermes summary')
    hermes_summary.add_argument('--hermes-id', required=True, help='Hermes agent ID')
    hermes_summary.add_argument('--text', required=True, help='Summary text')
    hermes_summary.add_argument('--scope', default='observe', help='Authority scope')

    # Hermes events
    hermes_events = hermes_sub.add_parser('events', help='List Hermes-filtered events')
    hermes_events.add_argument('--hermes-id', required=True, help='Hermes agent ID')
    hermes_events.add_argument('--limit', type=int, default=20, help='Max events to show')

    # Hermes list
    hermes_list = hermes_sub.add_parser('list', help='List all paired Hermes agents')

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
        if args.hermes_command == 'pair':
            return cmd_hermes_pair(args)
        elif args.hermes_command == 'status':
            return cmd_hermes_status(args)
        elif args.hermes_command == 'summary':
            return cmd_hermes_summary(args)
        elif args.hermes_command == 'events':
            return cmd_hermes_events(args)
        elif args.hermes_command == 'list':
            return cmd_hermes_list(args)
        else:
            hermes.print_help()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
