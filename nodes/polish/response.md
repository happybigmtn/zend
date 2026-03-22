All verified. The spec accurately reflects the actual repo state. Here's the summary:

## Documentation & Onboarding — Polish Complete

**Created artifacts:**

| Artifact | Path | Status |
|---|---|---|
| `spec.md` | `outputs/documentation-and-onboarding/spec.md` | ✅ Complete (275 lines) |
| `review.md` | `outputs/documentation-and-onboarding/review.md` | ✅ Complete (250 lines) |

**What the spec defines:**
- 5 required documentation artifacts with exact locations and content requirements
- README.md quickstart (5 steps verified against actual scripts)
- contributor-guide.md (dev setup)
- operator-quickstart.md (home hardware deployment)
- api-reference.md (all 7 scripts + 10 error codes verified against actual files)
- architecture.md (diagrams + module explanations)

**What the review finds:**
- `README.md` ✅ — already complete and meets spec
- `docs/contributor-guide.md` ⚠️ — missing, must be created
- `docs/operator-quickstart.md` ⚠️ — missing, must be created
- `docs/api-reference.md` ⚠️ — missing, must be created
- `docs/architecture.md` ⚠️ — missing, must be created

**Consistency:** All terminology (`PrincipalId`, `GatewayCapability`, `MinerSnapshot`, `EventSpine`, `HermesAdapter`), all 7 script names, all 10 error codes, and all 6 reference contracts verified against actual files. The documentation set will be consistent.