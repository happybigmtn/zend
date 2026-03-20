# Observability

**Status:** Contract for Milestone 1
**Last Updated:** 2026-03-19

## Structured Log Events

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
| `gateway.inbox.appended` | `event_kind`, `principal_id` | Event appended to spine |
| `gateway.inbox.append_failed` | `event_kind`, `reason` | Event append failed |
| `gateway.hermes.summary_appended` | `summary_id` | Hermes summary added |
| `gateway.hermes.unauthorized` | `action`, `scope` | Hermes unauthorized |
| `gateway.audit.local_hashing_detected` | `evidence` | Audit fails |

## Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `gateway_pairing_attempts_total` | Counter | `outcome` (success/rejected) |
| `gateway_status_reads_total` | Counter | `freshness` (fresh/stale) |
| `gateway_control_commands_total` | Counter | `outcome` (accepted/rejected/conflicted) |
| `gateway_inbox_appends_total` | Counter | `event_kind`, `outcome` |
| `gateway_hermes_actions_total` | Counter | `action`, `outcome` |
| `gateway_audit_failures_total` | Counter | `client` |

## Audit Log Records

Each audit record includes:
- timestamp (ISO 8601)
- principal_id
- event_type
- device_name
- outcome
- relevant_context

## Log Format

Structured JSON logging:
```json
{
  "timestamp": "2026-03-19T23:59:00Z",
  "level": "info",
  "event": "gateway.pairing.succeeded",
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"]
}
```
