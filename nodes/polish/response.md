Documentation is now accurate. Summary of corrections made:

## Polished Artifacts

**Files corrected:**

1. **`docs/api-reference.md`** - Reverted incorrect changes. API responses correctly show enum names (`MinerStatus.STOPPED`, `MinerMode.PAUSED`) not lowercase values. Clarified events are CLI-only.

2. **`README.md`** - Already had correct enum format, no changes needed.

3. **`outputs/documentation-and-onboarding/spec.md`** - Added note about Python `str`-inherit Enum serialization behavior. Updated events endpoint note to indicate CLI-only.

4. **`outputs/documentation-and-onboarding/review.md`** - Complete rewrite with accurate verification results documenting the enum serialization finding and corrections.

**Key findings documented:**

- Python `str`-inherit Enums serialize using the member **name** (`MinerStatus.STOPPED`) not the member **value** (`stopped`)
- Event spine is accessible only via CLI, not via HTTP endpoint
- All curl examples verified against running daemon