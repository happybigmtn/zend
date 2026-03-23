Both durable artifacts are polished and ready.

**`spec.md`** — now structured as a proper as-built spec with:
- Repo context linking to `DESIGN.md`/`SPEC.md` Zend conventions
- Full symbol table for `hermes.py` with done/partial/done states
- Endpoint table for `daemon.py` with auth methods
- Verified behavior section with 5 concrete confirmations
- Gap analysis with root causes, impacts, and named fix options (not vague TODOs)
- Frontier task matrix mapped to actual vs. intended with explicit gap references
- Supervisory plane notes with a clear sign-off gate statement

**`review.md`** — now structured as an honest review with:
- Verdict up top (readable in 30 seconds)
- Three findings with concrete evidence, impact, and named fix options (not just descriptions)
- Fix applied during review documented separately from the findings
- Supervisory action items table: priority, action, owner columns
- Verification environment noted for reproducibility

Key clarification added to both: the daemon.py duplication issue was **already fixed** during the previous review pass — the current `daemon.py` is clean and correct. The three remaining blockers are Gap 1 (runtime auth keyed by `hermes_id` not token), Gap 2 (expiration malformed), and Gap 3 (no tests).