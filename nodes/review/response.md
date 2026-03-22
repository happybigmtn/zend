`★ Insight ─────────────────────────────────────`
The core pattern here is **documentation-as-hallucination**: the spec model read `spine.py`'s function signatures (`get_events`, `append_hermes_summary`) and `store.py`'s types (`token_expires_at`, `token_used`) and inferred HTTP endpoints and CLI commands that *should* exist but *don't*. This is the docs equivalent of an LLM writing import statements for packages that don't exist. The fix is mechanical verification: for every documented command, grep the actual route table or argparse tree.
`─────────────────────────────────────────────────`

---

## Review Summary

**Verdict: REVISE** — 8 blocking issues prevent merge.

### What's wrong

**Correctness (3 critical):**
- **3 phantom API endpoints** in api-reference.md (`GET /spine/events`, `GET /metrics`, `POST /pairing/refresh`) — none exist in `daemon.py`
- **1 phantom CLI subcommand** (`cli.py devices`) referenced in operator-quickstart but not implemented
- **README quickstart step 5 fails** — bootstrap grants `observe` only, but step 5 sends a `control` command

**Correctness (5 more):**
- `source .env` doesn't export variables to child processes
- "Encrypted event journal" is plaintext JSON
- Duplicate `scripts/` section in README
- CORS headers missing from daemon (breaks LAN-served HTML gateway)
- Daemon's lack of HTTP auth not called out for operators

**Security (Nemesis):**
- The daemon HTTP API has **zero authentication** — any LAN peer can control the miner directly via curl, bypassing the CLI's capability checks entirely
- Pairing tokens are scaffolded data with no enforcement (`token_expires_at` is set to creation time, `token_used` is never checked)
- Store/spine writes are not atomic or transactionally coupled — crash during `cmd_pair` can leave divergent state
- `kill -9` after 1 second in bootstrap script can corrupt state files
- `rm -rf state/` as primary recovery destroys all audit history

### What's good

- `contributor-guide.md` is accurate and thorough
- Architecture diagrams correctly represent actual module relationships
- Writing quality and structure are strong across all docs
- systemd unit file and troubleshooting sections are practical

### Artifacts produced

- `outputs/documentation-and-onboarding/review.md` — full review with findings
- `outputs/documentation-and-onboarding/spec.md` — acceptance criteria and remaining work