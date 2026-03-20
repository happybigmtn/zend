#!/usr/bin/env python3
"""
Hermes Adapter CLI

Command-line interface for Hermes adapter operations.
"""

import argparse
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_adapter import HermesAdapter, HermesSummary, HermesCapability
from authority import (
    encode_authority_token,
    decode_authority_token,
    load_hermes_token,
    save_hermes_token,
)


def cmd_connect(args):
    """Connect to Zend gateway with authority token."""
    adapter = HermesAdapter(gateway_url=args.gateway_url)

    token = args.token or load_hermes_token()
    if not token:
        print("Error: No authority token provided and none saved.")
        print("Generate one with: hermes-adapter-cli.py token --capabilities observe,summarize")
        sys.exit(1)

    try:
        conn = adapter.connect(token)
        print(f"Connected: {conn.connection_id}")
        print(f"Principal: {conn.principal_id}")
        print(f"Capabilities: {[c.value for c in conn.capabilities]}")
        print(f"Expires: {conn.expires_at}")
    except ValueError as e:
        print(f"Connection failed: {e}")
        sys.exit(1)


def cmd_status(args):
    """Read miner status (requires observe capability)."""
    adapter = HermesAdapter(gateway_url=args.gateway_url)

    token = args.token or load_hermes_token()
    if not token:
        print("Error: No authority token provided")
        sys.exit(1)

    try:
        adapter.connect(token)
        snapshot = adapter.readStatus()
        print(f"Status: {snapshot.status}")
        print(f"Mode: {snapshot.mode}")
        print(f"Hashrate: {snapshot.hashrate_hs} hs")
        print(f"Temperature: {snapshot.temperature}°C")
        print(f"Uptime: {snapshot.uptime_seconds}s")
        print(f"Freshness: {snapshot.freshness}")
    except PermissionError as e:
        print(f"Permission denied: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_summarize(args):
    """Append a Hermes summary (requires summarize capability)."""
    adapter = HermesAdapter(gateway_url=args.gateway_url)

    token = args.token or load_hermes_token()
    if not token:
        print("Error: No authority token provided")
        sys.exit(1)

    summary = HermesSummary(
        summary_text=args.text,
        authority_scope=args.scope.split(",") if args.scope else ["observe"],
    )

    try:
        adapter.connect(token)
        adapter.appendSummary(summary)
        print("Summary appended to event spine")
    except PermissionError as e:
        print(f"Permission denied: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_token(args):
    """Generate a new Hermes authority token."""
    capabilities = args.capabilities.split(",") if args.capabilities else ["observe"]

    # Validate capabilities
    valid = {"observe", "summarize"}
    for cap in capabilities:
        if cap not in valid:
            print(f"Error: Invalid capability '{cap}'. Must be one of: {valid}")
            sys.exit(1)

    # Get principal from existing state
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "home-miner-daemon"))
    from store import load_or_create_principal

    principal = load_or_create_principal()

    token = encode_authority_token(
        principal_id=principal.id,
        capabilities=capabilities,
    )

    if args.save:
        save_hermes_token(token)
        print(f"Token saved to state directory")

    print(f"Principal: {principal.id}")
    print(f"Capabilities: {capabilities}")
    print(f"Token: {token}")


def cmd_scope(args):
    """Show current authority scope."""
    adapter = HermesAdapter(gateway_url=args.gateway_url)

    token = args.token or load_hermes_token()
    if not token:
        print("Not connected (no token)")
        sys.exit(0)

    try:
        adapter.connect(token)
        scope = adapter.get_scope()
        print(f"Connected: {adapter._connection.connection_id}")
        print(f"Scope: {[c.value for c in scope]}")
    except ValueError as e:
        print(f"Invalid token: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Zend Hermes Adapter CLI")
    parser.add_argument(
        "--gateway-url",
        default=os.environ.get("ZEND_GATEWAY_URL", "http://127.0.0.1:8080"),
        help="Zend gateway URL",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # connect
    p_connect = subparsers.add_parser("connect", help="Connect to Zend gateway")
    p_connect.add_argument("--token", help="Authority token")

    # status
    p_status = subparsers.add_parser("status", help="Read miner status")
    p_status.add_argument("--token", help="Authority token")

    # summarize
    p_sum = subparsers.add_parser("summarize", help="Append Hermes summary")
    p_sum.add_argument("--token", help="Authority token")
    p_sum.add_argument("--text", required=True, help="Summary text")
    p_sum.add_argument("--scope", default="observe", help="Authority scope (comma-separated)")

    # token
    p_token = subparsers.add_parser("token", help="Generate authority token")
    p_token.add_argument("--capabilities", default="observe", help="Comma-separated capabilities")
    p_token.add_argument("--save", action="store_true", help="Save token to state")

    # scope
    p_scope = subparsers.add_parser("scope", help="Show current scope")
    p_scope.add_argument("--token", help="Authority token")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "connect":
        cmd_connect(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "summarize":
        cmd_summarize(args)
    elif args.command == "token":
        cmd_token(args)
    elif args.command == "scope":
        cmd_scope(args)


if __name__ == "__main__":
    main()