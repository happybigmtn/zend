# CI/CD Pipeline — Specification

**Status:** Milestone 1 Complete
**Generated:** 2026-03-22

## Overview

GitHub Actions workflow for Zend's `home-miner-daemon` service, providing automated test, lint, and security scanning on every push and pull request to `main`.

## Scope

| Deliverable | Status |
|-------------|--------|
| GitHub Actions workflow | Implemented |
| Test job (pytest + coverage) | Implemented |
| Lint job (ruff) | Implemented |
| Security scan (bandit) | Implemented |
| No-hashing audit step | Implemented |
| Branch protection for main | Manual — requires `gh` CLI |

## Pipeline Architecture

**Workflow file:** `.github/workflows/ci.yml`

### Jobs

| Job | Trigger | Purpose |
|-----|---------|---------|
| `test` | Every push/PR to main | pytest + 80% coverage threshold |
| `lint` | Every push/PR to main | ruff check + format validation |
| `security` | Every push/PR to main | bandit scan + no-hashing audit |

### Execution Environment

- Runner: `ubuntu-latest`
- Python: `3.12` (via `actions/setup-python@v5`)

## Job Details

### Test Job

```yaml
- Install: pytest, pytest-cov
- Run: pytest services/home-miner-daemon/ -v --tb=short
- Coverage: --cov=services/home-miner-daemon --cov-fail-under=80
```

### Lint Job

```yaml
- Install: ruff
- Check: ruff check services/home-miner-daemon/
- Format: ruff format --check services/home-miner-daemon/
```

### Security Job

```yaml
- Install: bandit
- Scan: bandit -r services/home-miner-daemon/ -ll
- Audit: bash scripts/no_local_hashing_audit.sh --client apps/zend-home-gateway/index.html
```

## Pre-Existing Code Quality Fixes

The pipeline revealed and resolved these issues:

| File | Issue | Resolution |
|------|-------|------------|
| `services/home-miner-daemon/cli.py:163` | Unused `pairing` variable | Removed dead code |
| `services/home-miner-daemon/cli.py` | Unused import `get_pairing_by_device` | Auto-fixed by ruff |
| `services/home-miner-daemon/cli.py` | Bandit B310 `urlopen` in local daemon | `# nosec B310` — intentional for localhost |
| 5 Python files | Incorrect formatting | `ruff format` applied |

## Verification

All checks pass locally:

```
✓ ruff check   — All checks passed
✓ ruff format  — 5 files already formatted
✓ bandit       — No issues (1 skipped via nosec)
✓ no-hashing audit — no local hashing detected
```

## Acceptance Criteria

- [x] `.github/workflows/ci.yml` is valid YAML
- [x] Three jobs defined: test, lint, security
- [x] Triggers on push and PR to main
- [x] ruff check passes
- [x] ruff format check passes
- [x] bandit scan passes
- [x] no-hashing audit runs
- [x] pytest runs with 80% coverage threshold

## Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions workflow |
| `outputs/ci-cd-pipeline/spec.md` | This specification |
| `outputs/ci-cd-pipeline/review.md` | Implementation review |

## Out of Scope

- Docker/containerized builds
- Multi-version Python matrix
- Deployment automation
- Branch protection (requires GitHub UI or `gh` CLI — see `review.md`)

## Branch Protection Configuration

Requires manual execution via `gh` CLI:

```bash
gh api repos/{owner}/{repo}/branches/main/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["test","lint","security"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1}'
```
