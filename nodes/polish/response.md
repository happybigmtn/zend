Both artifacts are now polished. Here's what changed:

**`spec.md` — Key improvements:**
- Removed the non-existent `genesis/plans/001-master-plan.md` reference
- Added a concrete **User-Visible Outcome** section with exact HTTP requests and expected behaviors
- Added **Authority Token Shape** as a JSON code block for clarity
- Tightened the **Module Interface** section to match actual function signatures in `hermes.py`
- Fixed the **Files Changed** table to reflect what was actually created/modified
- Added a dedicated **Acceptance Criteria** section with 8 numbered, testable criteria
- Cleaned up redundant sections that repeated info already in Architecture

**`review.md` — Key improvements:**
- Replaced the prose summary with a clean **Implementation Checklist** table matching the original frontier tasks
- Added **Design Decisions** section with the 5 key decisions and their trade-offs (was partially present but scattered)
- Added a dedicated **Security Analysis** section with three sub-analyses (token validation, event filtering, control blocking)
- Removed the inconsistent "DONE" checkbox annotation that conflicted with the checkmark
- Consolidated **Open Items** into a proper table with status
- Made the **Sign-off** section concise and definitive