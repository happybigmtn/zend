Both artifacts are polished. Here's what changed and why:

---

**`spec.md` — Capability Spec**

- Anchored to `references/hermes-adapter.md` as the source contract throughout
- Added a "What Exists After This Slice" section so a reader landing here cold knows exactly what was built and where
- Consolidated the data models into compact reference tables (prevents prose drift)
- Replaced the generic "Out of Scope" with explicit per-item rationale and a separate "Security Gaps" section that distinguishes LAN-acceptable gaps from deployment blockers
- The capability table, event filtering allowlist, and HTTP endpoint table are now the primary structure instead of prose — easier for a supervisory plane to audit against the source contract
- BLOCKER-1 (control endpoint protection gap) is now listed as an explicit acceptance criterion with **Gap** status, making it unmissable

**`review.md` — Post-Implementation Review**

- Laid out the verdict first, then the evidence — supervisory plane reads top-to-bottom and gets the answer immediately
- Three bugs are named (BUG-1/2/3) with severity, root cause, impact, and fix for each
- Dangerous actions table makes the attack surface legible at a glance
- Blockers are now two-tier: must-fix (BLOCKER-1) vs. should-fix-before-network (SEC-1/2/3), each with a concrete remediation option
- Coupled-state review focuses on the store-sharing concern and idempotence properties that would matter most in a production incident