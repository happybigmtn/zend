`★ Insight ─────────────────────────────────────`
**Why unsigned tokens are acceptable in milestone 1 but dangerous later:**
The Hermes adapter uses plaintext JSON tokens with no HMAC or signature. On a LAN-only binding (`127.0.0.1`), the attacker must already be on the machine — at which point they can read `pairing-store.json` directly. So the token adds no real attack surface. But the moment the daemon binds to a LAN interface (`192.168.x.x`), any device on the network can forge tokens by guessing hermes_id + principal_id. The transition from `127.0.0.1` to LAN binding is the security cliff — token signing must land before that change.
`─────────────────────────────────────────────────`

## Review Complete

**Verdict: CONDITIONALLY APPROVED**

### 3 bugs fixed

| Bug | Severity | Fix |
|-----|----------|-----|
| Duplicate `do_GET` shadowing | Code defect | Removed dead first definition (`daemon.py`) |
| Auth header expected JSON, plan documents plain hermes_id | **Blocking** | Rewrote `_get_hermes_auth` to look up pairing by hermes_id (`daemon.py`) |
| `list_devices()` crash after Hermes pairing | **Crash** | Skip `hermes:` keys in iteration (`store.py`) |

### 1 remaining blocker

**Control endpoint protection.** The plan's acceptance criteria require that Hermes calling `/miner/start` returns 403. Currently all miner control endpoints are unauthenticated. Either:
- Add a guard to `/miner/*` that rejects `Authorization: Hermes` headers, or
- Revise acceptance criteria to defer Hermes control rejection until device auth lands

### Artifacts delivered

- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`