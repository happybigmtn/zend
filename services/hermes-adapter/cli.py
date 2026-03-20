#!/usr/bin/env python3
"""
Hermes Adapter CLI - Test and manage Hermes adapter connections.

Usage:
    python3 cli.py connect [--token <authority_token>]
    python3 cli.py status
    python3 cli.py summary --text "<summary_text>"
    python3 cli.py scope
    python3 cli.py disconnect
"""
import argparse
import base64
import json
import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from adapter import HermesAdapter, HermesCapability, HermesSummary


def cmd_connect(args):
    """Connect to Zend gateway with authority token."""
    adapter = HermesAdapter.from_state()

    if args.token:
        token = args.token
    else:
        # Generate demo token for testing
        token_data = {
            "principal_id": "hermes-demo-principal",
            "capabilities": ["observe", "summarize"],
            "expires_at": None
        }
        token = base64.b64encode(json.dumps(token_data).encode()).decode()

    try:
        connection = adapter.connect(token)
        print(json.dumps({
            "connected": True,
            "connection_id": connection.connection_id,
            "principal_id": connection.principal_id,
            "capabilities": [c.value for c in connection.capabilities],
            "connected_at": connection.connected_at
        }, indent=2))
    except Exception as e:
        print(json.dumps({"connected": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Read current miner status."""
    adapter = HermesAdapter.from_state()

    if not adapter.isConnected():
        print(json.dumps({"error": "not connected"}), file=sys.stderr)
        sys.exit(1)

    try:
        snapshot = adapter.readStatus()
        if snapshot:
            print(json.dumps({
                "status": snapshot.status,
                "mode": snapshot.mode,
                "hashrate_hs": snapshot.hashrate_hs,
                "temperature": snapshot.temperature,
                "uptime_seconds": snapshot.uptime_seconds,
                "freshness": snapshot.freshness
            }, indent=2))
        else:
            print(json.dumps({"status": "unknown"}))
    except PermissionError as e:
        print(json.dumps({"error": str(e), "capability_required": "observe"}), file=sys.stderr)
        sys.exit(1)


def cmd_summary(args):
    """Append a Hermes summary to the event spine."""
    adapter = HermesAdapter.from_state()

    if not adapter.isConnected():
        print(json.dumps({"error": "not connected"}), file=sys.stderr)
        sys.exit(1)

    from datetime import datetime, timezone
    summary = HermesSummary(
        summary_text=args.text,
        authority_scope=[c.value for c in adapter.getScope()],
        generated_at=datetime.now(timezone.utc).isoformat()
    )

    try:
        event_id = adapter.appendSummary(summary)
        print(json.dumps({
            "event_id": event_id,
            "summary_text": summary.summary_text,
            "authority_scope": summary.authority_scope
        }, indent=2))
    except PermissionError as e:
        print(json.dumps({"error": str(e), "capability_required": "summarize"}), file=sys.stderr)
        sys.exit(1)


def cmd_scope(args):
    """Show current authority scope."""
    adapter = HermesAdapter.from_state()

    if not adapter.isConnected():
        print(json.dumps({"connected": False, "scope": []}))
        sys.exit(0)

    scope = adapter.getScope()
    print(json.dumps({
        "connected": True,
        "scope": [c.value for c in scope]
    }, indent=2))


def cmd_disconnect(args):
    """Disconnect from Zend gateway."""
    adapter = HermesAdapter.from_state()
    adapter.disconnect()
    print(json.dumps({"disconnected": True}))


def main():
    parser = argparse.ArgumentParser(description="Hermes Adapter CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # connect
    p_connect = subparsers.add_parser("connect", help="Connect to Zend gateway")
    p_connect.add_argument("--token", help="Authority token (base64 or JSON)")
    p_connect.set_defaults(func=cmd_connect)

    # status
    p_status = subparsers.add_parser("status", help="Read miner status")
    p_status.set_defaults(func=cmd_status)

    # summary
    p_summary = subparsers.add_parser("summary", help="Append Hermes summary")
    p_summary.add_argument("--text", required=True, help="Summary text")
    p_summary.set_defaults(func=cmd_summary)

    # scope
    p_scope = subparsers.add_parser("scope", help="Show authority scope")
    p_scope.set_defaults(func=cmd_scope)

    # disconnect
    p_disconnect = subparsers.add_parser("disconnect", help="Disconnect")
    p_disconnect.set_defaults(func=cmd_disconnect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()