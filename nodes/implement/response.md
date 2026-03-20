## Implementation Complete

`★ Insight ─────────────────────────────────────`
The private control plane slice added HTTP API endpoints that were missing from the daemon. Previously, the CLI (`cli.py`) handled all spine event appends and capability checks directly without going through the HTTP interface. Now the daemon exposes `/spine/events` and `/inbox` endpoints that enforce the contracts defined in `inbox-contract.md` and `event-spine.md`.

The key architectural decision was using `Authorization: Bearer <device_name>` header to identify the calling device, rather than a session token. This allows the daemon to check capabilities against the pairing store without requiring a separate auth service.
`─────────────────────────────────────────────────`

### Changes to `services/home-miner-daemon/daemon.py`

**New HTTP endpoints:**
- `GET /spine/events` — reads events from spine, filtered by `principal_id`
- `GET /inbox` — derived view with routing destinations per event-spine.md

**Capability enforcement added:**
- Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) now require `Authorization: Bearer <device>` with `control` capability

**Spine event appends:**
- Successful control operations now append `control_receipt` events to the spine

### Artifacts Created

| Artifact | Purpose |
|----------|---------|
| `outputs/private-control-plane/implementation.md` | Describes changes made |
| `outputs/private-control-plane/verification.md` | Records proof commands and results (9/9 PASS) |
| `outputs/private-control-plane/quality.md` | Quality gate placeholder |
| `outputs/private-control-plane/integration.md` | Integration points with other modules |
| `outputs/private-control-plane/promotion.md` | Promotion gate placeholder (Settle stage) |

### Known Issue

The daemon startup on ports with TIME_WAIT sockets fails with "Address already in use" despite `SO_REUSEADDR`. This is a pre-existing issue, not introduced by this slice. Workaround: use a different port or wait for TIME_WAIT to clear.