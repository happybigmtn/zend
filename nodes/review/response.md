`★ Insight ─────────────────────────────────────`
**The "trust enforcement layer" problem** is one of the most common patterns in milestone-1 implementations: the data model defines capabilities correctly (PrincipalId, GatewayCapability), the documentation describes enforcement correctly (observe vs. control scoping), but the enforcement happens at the wrong layer (CLI wrapper instead of daemon HTTP boundary). The gateway client bypasses it entirely. This is not a bug — it's an architectural gap where the trust boundary is documented in one place and enforced in another, creating a false sense of security that compounds as more consumers are added.

**The born-expired token** is a subtle but load-bearing defect: `create_pairing_token()` sets `expires = datetime.now()`, meaning every token is expired at birth. Combined with the fact that no code path checks expiration, this means the entire pairing ceremony is theatrical — it creates data structures but enforces nothing.
`─────────────────────────────────────────────────`

---

**Review delivered** at `outputs/carried-forward-build-command-center/review.md`.

**Verdict: CONDITIONAL.** The scaffold is structurally sound — data model, information architecture, component vocabulary, and script operator flow all align with the spec. But the trust model the spec promises does not exist at runtime.

**5 must-fix blockers before graduation:**

1. **Daemon has zero authentication** — capability enforcement lives only in the CLI; the gateway client and any HTTP caller bypass it entirely
2. **Pairing tokens are born expired and never validated** — `PairingTokenExpired` and `PairingTokenReplay` can never fire
3. **Event spine writes plaintext** — spec promises "encrypted event journal," implementation writes cleartext JSONL
4. **Zero automated tests** — plan requires at least one per script
5. **Missing `gateway-proof.md`** — no runnable proof transcripts

**Additional critical findings:**
- Hermes smoke test bypasses the adapter entirely (direct spine import, no authority check)
- Shell injection pattern in `hermes_summary_smoke.sh` (bash variable interpolation into Python string literal)
- Control command serialization doesn't exist (`ControlCommandConflict` never raised)
- Staleness detection absent (`MinerSnapshotStale` never raised)
- Gateway client colors diverge from DESIGN.md palette
- No CORS headers (blocks LAN phone-to-daemon access)