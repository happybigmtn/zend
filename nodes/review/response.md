`★ Insight ─────────────────────────────────────`
**Why the prior review missed the daemon auth gap:** The MiniMax review tested the system through the CLI path (which does check capabilities) and concluded the capability model works. But the real attack surface is the HTTP API, which the gateway client calls directly. This is a common pattern in security reviews — testing through the intended flow and missing the bypass. A Nemesis review asks "what can an attacker reach?" not "does the happy path work?"

**Layered vs. perimeter auth:** The daemon has a perimeter (localhost binding) but no application-layer auth. This is fine for a dev simulator, but the spec describes a capability model that implies application-layer enforcement. The mismatch between what the spec promises and what the code delivers is the real finding.

**Store/spine consistency as a design smell:** When two stores (pairing-store.json and event-spine.jsonl) represent overlapping truth with no transaction boundary, divergence is inevitable. The event spine is declared "source of truth" but capability checks read from the pairing store. This dual-authority pattern needs to be resolved before production — either the spine becomes the read source for capabilities, or the pairing store becomes explicitly non-authoritative for audit purposes.
`─────────────────────────────────────────────────`

---

Review complete. The key findings that the prior review missed:

1. **The capability model is not enforced** — the daemon HTTP API has zero auth, the gateway client hardcodes `['observe', 'control']`, and any localhost process can control the miner directly. The prior review said "Capability scoping: Implemented" which is incorrect.

2. **The token lifecycle is entirely vestigial** — tokens are generated and immediately discarded. No token is stored, issued, or exchanged. The pairing "ceremony" is just registering a device name.

3. **CORS blocks the demo path** — the gateway client cannot talk to the daemon in a real browser without CORS headers.

4. **The event spine contract claims encryption that doesn't exist** — the spec is dishonest about current state.

5. **Shell injection** in `hermes_summary_smoke.sh` via unescaped string interpolation.

The recommendation is: fix daemon auth, CORS, and the spec's encryption claim before expanding surface area with Hermes or inbox work.