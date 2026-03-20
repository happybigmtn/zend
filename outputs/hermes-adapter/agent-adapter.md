# Hermes Adapter Agent Contract

**Status:** Milestone 1.1 Implementation
**Generated:** 2026-03-20

## Overview

Hermes Gateway connects to the Zend-native gateway contract through a Zend adapter. This keeps Zend future-proof and prevents Hermes from becoming the internal skeleton of the product.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter
      |
      v
Zend Gateway Contract
      |
      v
Event Spine
```

## Delegated Authority

In milestone 1, Hermes authority starts as:
- **Observe-only:** Hermes can read miner status
- **Summary append:** Hermes can append summaries to the event spine

Direct miner control through Hermes is NOT part of milestone 1.

## Capability Scope

```typescript
type HermesCapability = 'observe' | 'summarize';
```

## Adapter Interface

```typescript
interface HermesAdapter {
  // Connect to Zend gateway with delegated authority
  connect(authority_token: string): Promise<HermesConnection>;

  // Read current miner status (if observe granted)
  readStatus(): Promise<MinerSnapshot>;

  // Append summary to event spine (if summarize granted)
  appendSummary(summary: HermesSummary): Promise<void>;

  // Get current authority scope
  getScope(): HermesCapability[];
}

interface HermesConnection {
  // Unique connection identifier
  connectionId: string;

  // Principal ID this connection is authenticated as
  principalId: string;

  // Granted capabilities for this connection
  scope: HermesCapability[];

  // Connection expiration time
  expiresAt: string;  // ISO 8601

  // Close the connection
  close(): Promise<void>;
}

interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601
}

interface HermesSummary {
  summaryText: string;
  generatedAt: string;  // ISO 8601
  authorityScope: HermesCapability[];
}
```

## Event Spine Access

Hermes can read from event spine:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts it may have generated)
- `control_receipt` (to understand recent actions)

Hermes can write to event spine:
- `hermes_summary` (new summaries)

## Authority Token

The authority token is issued by the Zend gateway during the Hermes pairing flow. It encodes:
- Principal ID
- Granted capabilities
- Expiration time

Token format (JWT-like structure):
```typescript
interface AuthorityToken {
  principalId: string;
  scope: HermesCapability[];
  expiresAt: string;  // ISO 8601
  issuedAt: string;    // ISO 8601
  gatewayId: string;
}
```

## Boundaries

**Milestone 1 boundaries:**
- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages

These boundaries are enforced by the adapter before relaying any Hermes request.

## Connection Lifecycle

1. **Pairing Flow:**
   - Hermes initiates connection request
   - Zend gateway validates Hermes identity
   - Gateway issues limited authority token
   - Adapter receives token and establishes connection

2. **Active Connection:**
   - Hermes uses `readStatus()` for miner monitoring
   - Hermes uses `appendSummary()` to record summaries
   - Hermes uses `getScope()` to verify current permissions

3. **Connection Termination:**
   - Token expiration
   - Explicit `close()` call
   - Gateway revocation

## Error Handling

| Error | Meaning | Adapter Action |
|-------|---------|----------------|
| `INVALID_TOKEN` | Token malformed or signature invalid | Reject connection |
| `TOKEN_EXPIRED` | Authority token has expired | Reject, suggest re-pairing |
| `SCOPE_INSUFFICIENT` | Requested action not in granted scope | Reject with scope details |
| `GATEWAY_UNAVAILABLE` | Cannot reach Zend gateway | Retry with backoff |
| `SPINE_WRITE_FAILED` | Cannot append to event spine | Return error, Hermes retries |

## Milestone 1.1 vs 1.2

| Feature | Milestone 1.1 | Milestone 1.2 |
|----------|---------------|---------------|
| readStatus | ✓ | ✓ |
| appendSummary | ✓ | ✓ |
| getScope | ✓ | ✓ |
| Control commands | ✗ | ✓ |
| Inbox access | ✗ | ✓ |
| Direct miner commands | ✗ | ✓ |

## Dependencies

- `services/home-miner-daemon/spine.py` — Event spine implementation
- `references/hermes-adapter.md` — Original capability spec

## Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_hermes.sh` | Verify hermes-adapter slice is bootstrapped |
| `hermes_summary_smoke.sh` | Test Hermes summary append to spine |