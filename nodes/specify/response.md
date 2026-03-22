`★ Insight ─────────────────────────────────────`
**CI Pipeline Design Choices:**
1. **Three separate jobs (test, lint, security)** — Each runs independently so failures are isolated and parallelizable
2. **80% coverage threshold** — Enforces testing but allows for milestone 1 incomplete coverage
3. **`# nosec B310` on urlopen** — Correct pattern when security concern doesn't apply to local daemon communication
4. **No Docker** — Python stdlib-only project; container overhead unjustified at this scale
`─────────────────────────────────────────────────`

## Summary

CI/CD pipeline bootstrapped. All checks pass locally:

| Check | Status |
|-------|--------|
| YAML validation | ✓ |
| ruff check | ✓ |
| ruff format | ✓ |
| bandit scan | ✓ (1 nosec) |
| no-hashing audit | ✓ |

### Files Created

- `.github/workflows/ci.yml` — GitHub Actions workflow (3 jobs)
- `outputs/ci-cd-pipeline/spec.md` — Specification
- `outputs/ci-cd-pipeline/review.md` — Implementation review

### Pre-existing Issues Fixed

- Removed unused `pairing` variable and `get_pairing_by_device` import from `cli.py`
- Formatted all Python files with `ruff format`
- Added `# nosec B310` for intentional local daemon URLopen

### Known Gap

- **pytest exit 5** — No tests exist yet (plan 004). Test job will fail until tests are added.
- **Branch protection** — Requires manual GitHub UI configuration:

```bash
gh api repos/{owner}/{repo}/branches/main/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["test","lint","security"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1}'
```

### Next Steps

1. Implement tests (plan 004) to make test job pass
2. Configure branch protection manually in GitHub settings
3. Push workflow and verify CI runs on GitHub