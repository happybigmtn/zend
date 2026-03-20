`★ Insight ─────────────────────────────────────`
The bootstrap slice for `home-miner-service` establishes the core daemon contract that all future slices must adhere to. Key design decisions baked in:
1. **Threading lock on miner state** — ensures serialized control commands; two competing requests cannot both be acknowledged
2. **Event spine as source of truth** — the inbox is a *projection* of the spine, not a second store; this prevents the split-brain problem where receipts exist in two places
3. **Capability-scoped pairing** — `observe` and `control` are the only scopes in phase 1; `control` is required for any state-changing operation
`─────────────────────────────────────────────────`

**Bootstrap slice complete.** Created lane artifacts:

| Artifact | Purpose |
|----------|---------|
| `outputs/home-miner-service/implementation.md` | What was built, surfaces introduced, what's deferred |
| `outputs/home-miner-service/verification.md` | Preflight passed; all concrete steps verified; health surfaces catalogued |
| `outputs/home-miner-service/service-contract.md` | HTTP API, CLI commands, data models, error taxonomy |
| `outputs/home-miner-service/review.md` | Correctness review, milestone fit, blockers, verdict: **APPROVED** |

**Verified surfaces:**
- `GET /health`, `GET /status`, `POST /miner/start|stop|set_mode` — all return correct JSON
- Capability enforcement — observe-only clients correctly rejected for control actions with `GatewayUnauthorized`
- Event spine — append-only, readable by observe-capable clients
- `no_local_hashing_audit.sh` — passes, proves no mining work on client

**Pre-existing issues (not blockers):**
- `fetch_upstreams.sh` fails due to incorrect repo URLs in manifest — daemon works without these deps
- Port conflict on preflight re-run — teardown issue from zombie daemon process

**Next slice should address:**
1. Fix or remove broken upstream manifest URLs
2. Write automated tests
3. Capture `gateway-proof.md` transcripts
4. Write `onboarding-storyboard.md`