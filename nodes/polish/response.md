Both durable artifacts are polished. Here's a summary of what changed:

**`spec.md` — key changes:**
- Removed all references to non-existent genesis plan files (004, 009, 012, etc.)
- Removed the "Genesis Sprint" framing — it's repo documentation, not a sprint artifact
- Added concrete file paths and line references throughout
- Clarified each gap has a genesis plan number but that the files don't exist yet
- Made the data contracts precise (e.g., `version: 1` not `version: 1` on every event)
- Added an "Open — Mapped to Genesis Plans" table with real priorities
- Tightened the security model section with clear bullet points

**`review.md` — key changes:**
- Removed the "Genesis Sprint" reviewer block — replaced with a clean date + scope header
- Converted the conformance table from ✅/❌ to a clear Delivered / Not Yet Delivered split
- Made each gap self-contained: severity, file:line, quoted evidence, one-sentence fix, plan reference
- Kept the sign-off table but made it about the artifacts themselves, not a fictional sprint ceremony
- Cleaned up the file inventory to match the actual repo structure exactly
- Removed the "lessons learned" section which was editorial speculation