Created both required artifacts:

**`outputs/carried-forward-build-command-center/spec.md`**
- Capability spec for Home Miner Control Service
- Capability spec for Gateway Client
- Complete error taxonomy reference
- Architecture overview with system components
- Current implementation status table
- Remaining work mapped to genesis plans
- Constraints (must/must not)
- Verification steps with expected outcomes
- Decision log

**`outputs/carried-forward-build-command-center/review.md`**
- Executive summary: **substantially implemented**
- Architecture & contracts review (6/6 complete)
- Implementation review (6/6 working)
- Design system compliance (verified)
- Security properties assessment
- Strengths: complete spec layer, clean architecture, design discipline
- Weaknesses: token replay not enforced, no tests, Hermes adapter missing, inbox UX placeholder
- Risk assessment with likelihood/impact matrix
- Recommendations (immediate, short-term, medium-term)
- Genesis plan mapping for remaining work
- Full file inventory

**Key findings:**
- Core implementation is functional (daemon, pairing, status, control, event spine, gateway client)
- Specification layer is production-ready (6 reference contracts match implementation)
- Design system correctly applied (Space Grotesk, IBM Plex, calm colors, 44px touch targets)
- Token replay prevention gap identified (genesis plan 004)
- Remaining work properly scoped to genesis plans 004, 008, 009, 011, 012