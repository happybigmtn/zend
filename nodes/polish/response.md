Done. Both artifacts are written and ready for the supervisory plane:

**`outputs/hermes-adapter-implementation/spec.md`** (214 lines)
- States purpose, scope, and architecture with a system diagram
- Defines `HermesAdapter` / `HermesConnection` interface with `readStatus`, `appendSummary`, `getScope`
- Documents the event spine access rules (what Hermes may read/write; what's blocked)
- Names the four error types and their HTTP mappings
- Lists 10 acceptance criteria covering token validation, scope enforcement, replay protection, and `user_message` filtering

**`outputs/hermes-adapter-implementation/review.md`** (130 lines)
- Confirms architecture compliance against each requirement
- Confirms milestone fit against the master plan's Hermes tasks
- Documents three open gaps (tests, `disconnect()`, event filter mechanism)
- Flags two risks (token replay path untested, scope enforcement surface)
- Provides exact verification commands
- Delivers **APPROVED** verdict with remaining work called out explicitly