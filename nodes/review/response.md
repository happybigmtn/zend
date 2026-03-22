`★ Insight ─────────────────────────────────────`
**Why the phantom endpoints matter architecturally:** The docs describe `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh` as HTTP endpoints, but these functions only exist as Python imports called by `cli.py`. This reveals a design gap — the daemon was built as a minimal HTTP surface (5 routes), while the CLI does everything else as in-process calls. The documentation assumed a thicker HTTP API than was implemented. Fixing this is a design decision: either fatten the daemon's HTTP surface (so the UI can query events/metrics/pairing) or honestly document that these operations are CLI-only.

**The authorization gap is the most important finding.** The `index.html` command center directly calls `fetch('/miner/set_mode', ...)` — meaning any browser on the LAN has full control. The entire pairing/capability system only gates the CLI path, not the HTTP path. This is a trust boundary that the architecture doc actively misrepresents with its authorization flow diagram.
`─────────────────────────────────────────────────`

## Review Summary

**Status: FAILED** — 4 blocking issues, 1 critical security misrepresentation.

### Blocking Issues

1. **3 phantom endpoints** — `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` are documented with curl examples but return 404. They don't exist in `daemon.py`.

2. **Contributor guide control examples fail** — Bootstrap pairs `alice-phone` with `observe` only, but the guide shows `alice-phone` running control commands. Instant "unauthorized" error.

3. **Fabricated env var** — `ZEND_TOKEN_TTL_HOURS` in the operator quickstart doesn't exist anywhere in the codebase.

4. **Quickstart uses wrong device name** — Steps 4-5 reference `my-phone` which was never paired. Only `alice-phone` exists after bootstrap.

### Critical Security Finding

The HTTP API (`daemon.py`) has **zero authorization**. Any LAN client can start/stop/control the miner directly. Capability checks only exist in `cli.py`. The architecture doc draws an authorization flow diagram that implies the daemon enforces capabilities — it doesn't. The `index.html` command center confirms this: it calls the API with no auth tokens.

### What's Good

The documentation structure and readability are strong. The ASCII diagrams, systemd unit file, common-tasks guide, and design system reference are well done. The problems are factual accuracy, not quality of writing.

Full details in `outputs/documentation-and-onboarding/review.md`.