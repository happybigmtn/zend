**Polish complete.** Summary of fixes:

### Documentation fixes:
1. **README.md** (148 lines, under 200 limit):
   - Added `ZEND_DAEMON_URL` environment variable (was missing)
   - Fixed `open` command to show cross-platform alternatives

2. **docs/contributor-guide.md**:
   - Added explicit note that test suite doesn't exist yet
   - Fixed test command to acknowledge no tests exist

3. **docs/architecture.md**:
   - Removed non-existent `ZEND_TOKEN_TTL_HOURS`
   - Added `ZEND_DAEMON_URL` (which IS used by cli.py)
   - Fixed duplicate line
   - Added note about test infrastructure placeholder

4. **docs/api-reference.md**: No changes needed (was already clean)

### Durable artifacts updated:
- **`outputs/documentation-and-onboarding/spec.md`**: Added implementation notes about fixes made
- **`outputs/documentation-and-onboarding/review.md`**: Updated with discoveries and fixes

### Key discrepancies resolved:
| Issue | Resolution |
|-------|------------|
| `ZEND_TOKEN_TTL_HOURS` in docs but not code | Removed from all docs |
| `ZEND_DAEMON_URL` in code but not docs | Added to README, architecture |
| No tests exist but contributor guide implied they do | Added explicit notes |
| `open` command is macOS-only | Added Linux alternatives |