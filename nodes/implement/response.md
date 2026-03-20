`★ Insight ─────────────────────────────────────`
1. **Port configuration via environment variables** is the standard pattern for service configuration - the daemon reads `ZEND_BIND_PORT` at startup, allowing different deployment environments to configure ports without code changes. The frontend fix uses `window.location.port` to auto-detect the port when served via HTTP.

2. **The event spine pattern** (append-only JSONL journal) provides an immutable audit trail - events are only appended, never modified or deleted. This simplifies debugging and enables replaying history, critical for financial/compliance applications.

3. **Capability-based authorization** (observe/control) follows the principle of least privilege - devices only get the minimum permissions they need, reducing blast radius if a device is compromised.
`─────────────────────────────────────────────────`

## Summary

Completed the `home-miner-service:home-miner-service` implementation slice with all required artifacts:

| Artifact | Status | Description |
|----------|--------|-------------|
| `service-contract.md` | ✓ Created | HTTP API, CLI commands, data models, capability model |
| `review.md` | ✓ Created | Implementation review with correctness/milestone fit assessment |
| `implementation.md` | ✓ Created | Slice scope, components, file inventory, boundaries |
| `verification.md` | ✓ Created | 11 automated tests, all passing |
| `integration.md` | ✓ Created | Upstream/downstream integration, data flow, gaps |

**Slice delivered**: `milestone-1-bootstrapped` — functional home-miner daemon with HTTP API, CLI, pairing, and event spine.

**Bug fixed**: Frontend hardcoded port 8080, now uses `window.location.port` for dynamic port detection.