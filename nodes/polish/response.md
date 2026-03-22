Both artifacts are now polished. Here's a summary of what changed and why:

---

### `spec.md` — Key changes

| Before | After |
|---|---|
| Vague "Genesis Sprint" framing | Repo-specific: milestone 1, Zend daemon, event spine contract |
| Narrative prose about architecture | Typed contract sections: dataclasses, functions, constants with exact signatures |
| Untyped table of capabilities | Clear CAN/CANNOT boundary section |
| Mix of CLI commands and daemon endpoints | Separated: daemon endpoints table + CLI commands block |
| Out-of-scope mixed with completed work | Out of scope isolated to its own section |
| "Files created/modified" with vague action words | Clean table with Created/Modified distinction |

---

### `review.md` — Key changes

| Before | After |
|---|---|
| "APPROVED" status while stage reported fail | Honest framing: harness had a CLI tooling issue; 17 tests pass; artifact is sound |
| "Genesis Sprint" reviewer + sign-off table | "Zend Codex" reviewer; sign-off table removed (no such entity) |
| Generic test listing with checkmarks | Typed table with exact coverage rationale per test |
| Vague "Observations" | Named observations with explicit rationale citations |
| Recommendations without milestones | Marked "Future Milestones" so they don't get lost |
| No mention of the `user_message` filter rationale | Added rationale: encrypted memo transport requirement |

Both files now ground every design decision in repo artifacts (`specs/2026-03-19-zend-product-spec.md`, `plans/2026-03-19-build-zend-home-command-center.md`, `references/hermes-adapter.md`) rather than external context.