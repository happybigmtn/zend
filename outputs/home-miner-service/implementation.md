# Home Miner Service — Implementation

## Slice: Authorization Enforcement

**Status:** Complete
**Date:** 2026-03-20

## Overview

Implemented capability-based authorization enforcement at the daemon HTTP layer. This slice closes the gap between the pairing store (which correctly tracks device capabilities) and the HTTP endpoints (which previously accepted any request).

## Changes

### `services/home-miner-daemon/daemon.py`

**Added imports:**
- `import store` — to access pairing store for capability checks

**Added methods to `GatewayHandler`:**

1. `_get_device_from_auth() -> Optional[str]`
   - Parses `Authorization: Bearer <device_name>` header
   - Returns `None` if header is missing or malformed

2. `_require_capability(capability: str) -> Optional[dict]`
   - Checks if the authenticated device has the required capability
   - Returns `None` if authorized
   - Returns `{"error": "GATEWAY_UNAUTHORIZED", "message": "..."}` if unauthorized

**Modified endpoints:**

- `POST /miner/start` — now requires `control` capability
- `POST /miner/stop` — now requires `control` capability
- `POST /miner/set_mode` — now requires `control` capability

**Unchanged endpoints:**
- `GET /health` — no auth required (public health check)
- `GET /status` — no auth required (read-only status)

**Error responses use `GATEWAY_UNAUTHORIZED` code per error taxonomy.**

## Authorization Flow

```
Request + Authorization: Bearer <device_name>
         |
         v
   Parse device name from header
         |
         v
   Lookup device in pairing store
         |
         v
   Check if device has required capability
         |
         +--[has capability]--> Execute action
         |
         +--[missing header]--> 403 GATEWAY_UNAUTHORIZED
         |
         +--[lacks capability]--> 403 GATEWAY_UNAUTHORIZED
```

## Test Evidence

```
=== Test 1: No Authorization header on /miner/start ===
{"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}

=== Test 2: alice-phone (observe-only) calling /miner/start ===
{"error": "GATEWAY_UNAUTHORIZED", "message": "This device lacks 'control' capability"}

=== Test 3: Health check (no auth required) ===
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

=== Test 4: bob-phone (control-capable) calling /miner/start ===
{"success": true, "status": "MinerStatus.RUNNING"}
```

## Slice Size

This is the smallest possible slice that closes the authorization gap. The change:
- Does not modify the pairing store schema
- Does not modify the event spine
- Does not modify the CLI (which already had client-side checks)
- Only modifies daemon.py to enforce server-side authorization

## Alignment with Plan

This slice implements the requirement from `plans/2026-03-19-build-zend-home-command-center.md`:

> "Restrict milestone 1 to LAN-only pairing and control."

And the error taxonomy item:

> `GatewayUnauthorized` — The gateway client lacks the required capability for the requested action.
