`★ Insight ─────────────────────────────────────`
The most architecturally interesting finding here is the **decoupled capability model**. The store/CLI/daemon form a three-layer stack where the middle layer (CLI) enforces access control, but neither the bottom (daemon HTTP) nor the top (web UI) participate. This is a common M1 pattern — build the identity model early, defer enforcement to when real network exposure arrives. The danger is documentation that conflates "the model exists" with "the model is enforced." The review's honesty clause is the key correction.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: SPEC ACCEPTED WITH CORRECTIONS — IMPLEMENTATION NOT STARTED**

The spec for the documentation-and-onboarding lane is structurally sound and well-scoped. Both required durable artifacts now exist (`spec.md` was already written; `review.md` is now delivered). Zero implementation artifacts exist — none of the 5 docs have been written, and the README has not been rewritten.

### Two mandatory corrections before implementation:

1. **Fix acceptance criterion 1** — the spec claims `/health` returns `{"status": "ok"}` but the actual response is `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`

2. **Add an honesty clause** — documentation must disclose that capability enforcement is CLI-side only, the daemon HTTP interface is unauthenticated, and pairing tokens are non-functional placeholders in M1

### Key Nemesis findings (not code bugs — documentation honesty requirements):

| Finding | Impact |
|---------|--------|
| Daemon HTTP has no auth | API reference must state "unauthenticated" |
| Capability checks are CLI-only | Must not claim endpoint-level authorization |
| Pairing tokens expire at creation | Must not describe token-based auth |
| Event spine not crash-safe | Architecture doc must note truncated-line risk |
| Bootstrap skips `pairing_requested` event | Note the audit trail asymmetry |

The full review is at `outputs/documentation-and-onboarding/review.md`.