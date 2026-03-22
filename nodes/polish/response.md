The files are correct. Here is a precise account of what was changed and why:

---

## Polish Summary

### `outputs/hermes-adapter-implementation/spec.md`

**What changed:**
- Removed all generic framework language ("Capabilities", "Architecture" boilerplate) and replaced it with Zend/Fabro-native terminology: lane, slice, supervisory plane, in-process adapter
- Rewrote the adapter interface section to be a precise capability contract — every function now has its exact behavior, token format, and error conditions described
- Added a **Decision Log** with four explicit decisions (in-process adapter, independent capability sets, filter in adapter not spine, plain-text token for milestone 1)
- Corrected the boundary table to be a precise enforcement matrix: which function enforces which boundary, and how
- Removed the "CLI Commands" section that duplicated daemon endpoint documentation — the CLI is an implementation detail, not part of the durable contract
- Added a "Future Expansion" section so out-of-scope items are explicit and not lost

### `outputs/hermes-adapter-implementation/review.md`

**What changed:**
- **Corrected Finding 1:** The original review described control rejection as "route-layer middleware." The implementation uses a direct `if` guard inside `do_POST`. The review now says this precisely, and notes the difference is low-impact but important for audit clarity
- Added **Finding 2:** `get_hermes_status()` and `hermes_read_status()` have confusingly similar names; one returns miner snapshot, the other returns Hermes connection status. Documented for future cleanup
- Added **Finding 3:** Token has no integrity mechanism (no HMAC, no signature). Accepted for milestone 1 but documented as a production gate
- Replaced vague "What's Working" narrative with a verification table that cites exact file locations and evidence from the code
- Added "Next Steps" that are concrete and actionable (test file, smoke script, rename, logging)