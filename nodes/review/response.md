`★ Insight ─────────────────────────────────────`
**Why the prior review was worse than useless:** The MiniMax-generated review rubber-stamped every item as "✅ tested" including phantom endpoints (`/spine/events`, `/gateway`) that don't exist and tests that don't exist. A false-positive review is worse than no review — it creates unearned confidence. This is the documentation equivalent of `catch(e) {}`.

**The CLI-only auth boundary is the core architectural gap:** The pairing/capability system only runs inside the CLI Python process. The HTTP daemon — the actual network-exposed surface — has zero auth. The docs describe the CLI auth flow as if it protects the API. This means the entire security narrative in the architecture doc and API reference is aspirational, not descriptive. Honest documentation would say: "Milestone 1 HTTP API is unauthenticated. Access control is enforced only through CLI commands. Do not bind to `0.0.0.0` without understanding this limitation."

**The `EventKind.value` bug is a type-system gap worth noting:** `get_events(kind)` annotates `kind: Optional[EventKind]` but the CLI passes a plain string. Python's lack of runtime type enforcement means this "works" until the filter path runs, at which point `"control_receipt".value` raises `AttributeError`. This is exactly the class of bug that mypy or runtime validation at the boundary would catch.
`─────────────────────────────────────────────────`

---

## Review Complete

**Verdict: REVISE.** The documentation-and-onboarding lane produced well-structured, readable docs but failed the accuracy bar in three critical dimensions:

**7 must-fix blockers:**

1. **Phantom `GET /spine/events`** — documented but doesn't exist in daemon
2. **Phantom `GET /gateway`** — operator quickstart sends users to a 404
3. **Broken `import services.home_miner_daemon.store`** — hyphens in directory name
4. **No tests exist** — docs reference `test_spine.py` and pytest commands that find nothing
5. **`ZEND_TOKEN_TTL_HOURS`** — documented env var that no code reads
6. **False auth narrative** — docs say "access controlled by pairing" but HTTP API has zero auth
7. **Spec proof text wrong** — claims `{"status": "ok"}` but no endpoint returns that

**Security (Nemesis):** The HTTP API is completely unauthenticated. The pairing/capability system only gates CLI commands, not HTTP requests. The token lifecycle is dead code (tokens expire at creation, are never validated, never marked used). The event spine is not a reliable audit trail since direct HTTP calls bypass it. The docs actively misrepresent these realities.

Full findings in `outputs/documentation-and-onboarding/review.md`.