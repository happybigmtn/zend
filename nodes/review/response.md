`★ Insight ─────────────────────────────────────`
**Why the prior review was unreliable:** The automated review checked structural completeness (all sections present, all headings exist) but never verified claims against source code. It's a checklist review, not a correctness review. The phantom endpoints passed because the review checked "does the doc have a section for GET /spine/events?" rather than "does the daemon handle GET /spine/events?". This is the difference between documentation *coverage* and documentation *accuracy*.

**The auth layer confusion is architectural:** The system has a split-brain auth model — capability enforcement in the CLI process, zero enforcement in the HTTP daemon. The HTML gateway talks directly to the daemon. This means the pairing/capability system is a CLI convenience, not a security boundary. The docs describe it as the latter.
`─────────────────────────────────────────────────`

---

**Verdict: CONDITIONAL PASS**

The documentation lane produced all required artifacts with good structure and coverage. The prior automated review was not honest — it claimed zero issues while multiple material inaccuracies exist.

**4 blockers before this slice is honest:**

1. **Phantom endpoints** — `GET /spine/events` and `POST /pairing/bootstrap` are documented as HTTP endpoints but don't exist in the daemon. They're CLI-only commands.

2. **Auth claims are fiction** — API reference says "Auth Required: Control capability" on POST endpoints. The daemon has zero auth checks. Any HTTP client controls the miner. The capability system only exists in the CLI layer, which the HTML gateway bypasses entirely.

3. **Quickstart step 5 fails** — Bootstrap creates `['observe']`-only pairing, but the quickstart immediately shows a `control` command that requires `control` capability.

4. **CLI `--kind` filter crashes** — `cli.py` passes a raw string to `spine.get_events()` which calls `.value` on it. `AttributeError` at runtime.

**Non-blocking issues:** undocumented env var (`ZEND_DAEMON_URL`), undocumented script (`read_miner_status.sh`), bootstrap non-idempotency, spine/miner state decoupling (direct HTTP ops don't produce spine events).

**What's good:** README structure, operator quickstart (strongest doc), architecture design decisions with trade-off analysis, design system compliance in the gateway, stdlib-only philosophy communicated clearly. The foundation is strong — fix accuracy and this slice ships.