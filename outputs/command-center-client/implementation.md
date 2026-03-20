# Command Center Client — Implementation

**Slice:** command-center-client:command-center-client
**Date:** 2026-03-20

## Slice Goal

Implement the onboarding flow for the Zend Home gateway client, completing the appliance-style onboarding storyboard step.

## What Was Implemented

### 1. Daemon Pairing API (`services/home-miner-daemon/daemon.py`)

Added HTTP endpoints for UI-driven pairing:

- `GET /pairing/status` — Returns paired state with device name, capabilities, principal ID
- `POST /pairing/initiate` — Creates pending pairing with 8-character short code
- `POST /pairing/confirm` — Confirms pairing, persists to store, returns pairing details

In-memory pending pairing state (`_pending_pairing` dict) stores short code for verification.

### 2. Onboarding UI (`apps/zend-home-gateway/index.html`)

Added 4 onboarding screens:

**Step 1 — Name Your Zend Home**
- Text input for home miner name (max 32 chars)
- Continue button (disabled until input provided)

**Step 2 — Choose Permissions**
- Observe capability (pre-selected, disabled)
- Control capability (optional checkbox)
- Explanatory text for each capability

**Step 3 — Pairing**
- 8-character short code display (monospace, large)
- Instructions for entering code
- Complete pairing button
- Back navigation

**Step 4 — Complete**
- Success confirmation with checkmark
- "Start Using Zend Home" button to enter main app

### 3. Onboarding Flow Logic

- `checkPairingStatus()` — Checks daemon on load, falls back to localStorage cache
- `showOnboardingStep(n)` — Navigates between onboarding screens
- `initiatePairing()` — Creates pending pairing via daemon API
- `confirmPairing()` — Confirms pairing and persists state

### 4. State Persistence

Added localStorage keys:
- `zend_home_name` — User-assigned home name
- `zend_capabilities` — JSON array of granted capabilities

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | Added pairing endpoints and state |
| `apps/zend-home-gateway/index.html` | Added onboarding screens and flow |

## Design Decisions

1. **Short code over QR** — Milestone 1 uses alphanumeric codes; QR deferred for future
2. **In-memory pending state** — Pairing tokens not persisted; cleared on confirm or restart
3. **Capability checkboxes** — Observe is always granted; control is optional grant
4. **LocalStorage fallback** — If daemon unreachable, uses cached pairing data from localStorage

## Relationship to Prior Art

Extends `home-command-center` gateway client with onboarding flow. Prior implementation assumed pre-existing pairing; this slice adds the missing onboarding ceremony per the storyboard.

## Verification

See `verification.md` for automated proof commands.
