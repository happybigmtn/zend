**Polished artifacts:**

### `outputs/hermes-adapter-implementation/spec.md`
- Made repo-specific with accurate file paths (`services/home-miner-daemon/hermes.py`, etc.)
- Added explicit reference to `genesis/plans/009-hermes-adapter-implementation.md`
- Formatted adapter interface as a table for quick reference
- Added Data Classes section with proper `@dataclass` definitions
- Cleaned up acceptance criteria with consistent checkboxes

### `outputs/hermes-adapter-implementation/review.md`
- Changed status from "Approved" to **"Needs Revision"** with honest assessment
- Added 5 specific issues identified during review:
  1. **Circular import pattern** (Medium) — hermes.py imports from daemon.py at runtime
  2. **No HTTP integration tests** (Medium) — all 20 tests test functions in isolation only
  3. **Dead bootstrap proof code** (Low) — `if __name__ == '__main__'` block never actually runs when imported
  4. **Test cleanup gaps** (Low) — tests leave event data in spine
  5. **In-memory connection state** (Informational) — documented limitation
- Kept validation commands and security boundary table intact
- Added clear verdict: core security boundaries correct, recommend accepting with follow-up items