**Fixup Complete**

Created the missing artifacts per the promotion.md next_action:

| Artifact | Status |
|----------|--------|
| `outputs/hermes-adapter/implementation.md` | Created |
| `outputs/hermes-adapter/verification.md` | Created |
| `./scripts/bootstrap_hermes.sh` | PASS (exit 0) |

**Proof gate output:**
```
Observe: status=stopped, mode=paused
Summarize: summary appended to event spine
[INFO] Hermes Adapter bootstrap complete
```

**Remaining issue:** The audit script also checks for `outputs/hermes-adapter/integration.md`, which is **not** in the required curated artifacts list (implementation, verification, quality, promotion). The promotion.md next_action only mentioned adding implementation.md and verification.md — it does not mention integration.md. This appears to be a discrepancy between the audit script and the lane artifact definition.

The settle stage owns promotion.md and should handle any promotion-related artifact creation. The fixup scope was to unblock the first proof gate by adding implementation.md and verification.md, which is complete.

`★ Insight ─────────────────────────────────────`
The lane's audit script checks for 5 files, but the curated artifacts list only defines 4. This is a structural mismatch — the settle stage (which writes promotion.md) should clarify whether integration.md is a required artifact or whether the audit script should be updated.
`─────────────────────────────────────────────────`