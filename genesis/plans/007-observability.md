# Genesis Plan 007: Observability

**Status:** Pending
**Priority:** Medium
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Implement structured logging, metrics collection, and audit logging as specified in `references/observability.md`.

## Requirements

### Structured Log Events

| Event | Fields | Trigger |
|-------|--------|---------|
| `gateway.bootstrap.started` | - | Bootstrap script starts |
| `gateway.bootstrap.failed` | `reason` | Bootstrap fails |
| `gateway.pairing.succeeded` | `device_name`, `capabilities` | Pairing completes |
| `gateway.pairing.rejected` | `device_name`, `reason` | Pairing fails |
| `gateway.status.read` | `device_name`, `freshness` | Status read |
| `gateway.status.stale` | `device_name`, `age_seconds` | Snapshot stale |
| `gateway.control.accepted` | `device_name`, `command`, `mode` | Control action accepted |
| `gateway.control.rejected` | `device_name`, `command`, `reason` | Control action rejected |
| `gateway.inbox.appended` | `event_kind`, `principal_id` | Event appended |
| `gateway.audit.local_hashing_detected` | `evidence` | Audit fails |

### Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `gateway_pairing_attempts_total` | Counter | `outcome` |
| `gateway_status_reads_total` | Counter | `freshness` |
| `gateway_control_commands_total` | Counter | `outcome` |
| `gateway_inbox_appends_total` | Counter | `event_kind`, `outcome` |

## Concrete Steps

1. Add logging library (structlog or custom JSON logger)
2. Add metrics library (prometheus-client)
3. Instrument all gateway events
4. Add metrics endpoint `/metrics`
5. Add structured log output

## Expected Outcome

- All gateway events logged with structured format
- Metrics exposed for Prometheus scraping
- Audit trail for compliance
