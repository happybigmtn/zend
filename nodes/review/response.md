`★ Insight ─────────────────────────────────────`
**Why the Nemesis review matters here:** This plan introduces the first *agent-to-system* trust boundary in Zend. Every prior interaction was human-to-system (gateway client with observe/control). Hermes is a different principal type — it's software acting with delegated authority. The review found that the existing codebase was built for a single trust model (LAN-local, human-operated) and the plan grafts a second trust model onto it without upgrading the underlying enforcement. The adapter is structurally correct but the *daemon itself* doesn't know the difference between a human client and a Hermes agent. That's the critical insight: the capability boundary lives in Python code, not in the HTTP layer. For M1 this is acceptable; for M2 it's a hard blocker.
`─────────────────────────────────────────────────`

## Summary

**Lane outcome: 0% implementation, plan reviewed and conditionally approved.**

### Artifacts delivered:
- `outputs/hermes-adapter-implementation/spec.md` — full specification with corrected interfaces
- `outputs/hermes-adapter-implementation/review.md` — Nemesis-style security review with 10 findings

### Source fixes made:
1. **`store.py`** — Fixed `create_pairing_token()` born-expired bug (now 24h TTL)
2. **`references/hermes-adapter.md`** — Resolved spec contradiction (user_message now explicitly blocked for Hermes)

### Key findings:
| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| H1 | No daemon auth — adapter boundary is bypassable | HIGH | Documented as M1 limitation |
| H2 | Authority token format doesn't exist | MEDIUM | Simplified to pairing-based auth |
| H3 | Token born-expired bug | MEDIUM | **Fixed** |
| H5 | Spec contradiction on user_message access | LOW | **Fixed** |
| H6 | Pairing namespace collision risk | MEDIUM | **Blocker** — needs design decision |
| H9 | authority_scope type mismatch (str vs list) | LOW | Corrected in spec |

### Remaining blocker before implementation:
**H6:** Hermes pairings share the same store namespace as gateway device pairings. A design decision is needed: separate store, type discriminator, or name prefix convention.