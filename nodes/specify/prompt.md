Goal: CI/CD Pipeline

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Create GitHub Actions workflow for Python tests
- Add linting step (ruff or flake8)
- Add security scan step (bandit or safety)
- Add the no-hashing audit as a CI step
- Configure branch protection for main
- Verify pipeline runs green on current codebase

Required durable artifacts:
- `outputs/ci-cd-pipeline/spec.md`
- `outputs/ci-cd-pipeline/review.md`



# CI/CD Pipeline Lane — Plan

Lane: `ci-cd-pipeline`

Goal:
- CI/CD Pipeline

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Create GitHub Actions workflow for Python tests
- Add linting step (ruff or flake8)
- Add security scan step (bandit or safety)
- Add the no-hashing audit as a CI step
- Configure branch protection for main
- Verify pipeline runs green on current codebase

Required durable artifacts:
- `outputs/ci-cd-pipeline/spec.md`
- `outputs/ci-cd-pipeline/review.md`

Context:
- Plan file:
- `genesis/plans/005-ci-cd-pipeline.md`

Full plan context (read this for domain knowledge, design decisions, and specifications):

# CI/CD Pipeline

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `genesis/PLANS.md`.

## Purpose / Big Picture

After this work, every push to the Zend repository triggers an automated pipeline that runs tests, checks code quality, and scans for security issues. A contributor sees a green or red badge on their PR before merging. No broken code reaches the main branch without a deliberate override.

## Progress

- [ ] Create GitHub Actions workflow for Python tests
- [ ] Add linting step (ruff or flake8)
- [ ] Add security scan step (bandit or safety)
- [ ] Add the no-hashing audit as a CI step
- [ ] Configure branch protection for main
- [ ] Verify pipeline runs green on current codebase

## Surprises & Discoveries

(To be updated during implementation.)

## Decision Log

- Decision: Use GitHub Actions, not GitLab CI or other.
  Rationale: The repo is hosted on GitHub (inferred from `gh` tooling and `.git` remote). GitHub Actions is the natural choice.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Keep CI simple — one workflow file, three jobs (test, lint, security).
  Rationale: The project is small (815 lines of Python). Complex CI with matrix builds or Docker containers is premature.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

(To be updated at completion.)

## Context and Orientation

Zend currently has no CI/CD pipeline. There is no `.github/workflows/` directory. The test suite (plan 004) must exist before this plan can fully execute, but the CI configuration can be authored first.

The project uses Python 3 with stdlib-only dependencies. The only dev dependency is pytest. Scripts are in bash. The frontend is a single HTML file with no build step.

## Plan of Work

### Milestone 1: Test Workflow (days 1–2)

Create `.github/workflows/ci.yml` with a test job that runs on every push and pull request:

    name: CI
    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
          - name: Install test dependencies
            run: pip install pytest pytest-cov
          - name: Run tests
            run: python3 -m pytest services/home-miner-daemon/ -v --tb=short
          - name: Run coverage
            run: |
              python3 -m pytest services/home-miner-daemon/ \
                --cov=services/home-miner-daemon \
                --cov-report=term-missing \
                --cov-fail-under=80

Proof:

    # Verify workflow file is valid YAML
    python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

### Milestone 2: Lint Job (days 2–3)

Add a lint job to the same workflow using `ruff` (fast Python linter):

    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.12'
        - name: Install ruff
          run: pip install ruff
        - name: Lint Python
          run: ruff check services/home-miner-daemon/
        - name: Check formatting
          run: ruff format --check services/home-miner-daemon/

Before adding CI, fix any existing lint issues locally:

    pip install ruff
    ruff check services/home-miner-daemon/ --fix
    ruff format services/home-miner-daemon/

Proof:

    ruff check services/home-miner-daemon/
    # Expected: All checks passed!
    ruff format --check services/home-miner-daemon/
    # Expected: would not reformat (or already formatted)

### Milestone 3: Security Scan Job (days 3–4)

Add a security job using `bandit` (Python security linter):

    security:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.12'
        - name: Install bandit
          run: pip install bandit
        - name: Security scan
          run: bandit -r services/home-miner-daemon/ -ll
        - name: No-hashing audit
          run: bash scripts/no_local_hashing_audit.sh --client apps/zend-home-gateway/index.html

The no-hashing audit (`scripts/no_local_hashing_audit.sh`) verifies the gateway client contains no mining/hashing code. Including it in CI ensures this invariant is never broken by future changes.

Proof:

    bandit -r services/home-miner-daemon/ -ll
    # Expected: No issues identified
    bash scripts/no_local_hashing_audit.sh --client apps/zend-home-gateway/index.html
    # Expected: exit 0, "No local hashing detected"

### Milestone 4: Branch Protection (day 4)

Configure GitHub branch protection for `main`:
- Require status checks to pass (test, lint, security jobs)
- Require pull request reviews (at least 1)
- No direct pushes to main

This is done via GitHub Settings UI or via `gh` CLI:

    gh api repos/{owner}/{repo}/branches/main/protection -X PUT -f \
      required_status_checks='{"strict":true,"contexts":["test","lint","security"]}' \
      -f enforce_admins=true \
      -f required_pull_request_reviews='{"required_approving_review_count":1}'

Proof:

    gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'
    # Expected: ["test", "lint", "security"]

### Milestone 5: Verify Green Pipeline (day 5)

Push the CI configuration and verify all jobs pass:

    git checkout -b ci/add-pipeline
    git add .github/workflows/ci.yml
    git commit -m "feat(ci): add test, lint, and security pipeline"
    git push -u origin ci/add-pipeline

Create a PR and verify all status checks pass:

    gh pr create --title "Add CI pipeline" --body "Adds GitHub Actions for test, lint, security"
    gh pr checks

Proof: `gh pr checks` shows all three jobs (test, lint, security) as passed.

## Validation and Acceptance

1. Every push to `main` triggers the CI pipeline
2. Tests, lint, and security scan all pass on the current codebase
3. The no-hashing audit runs in CI and passes
4. Branch protection prevents merging with failing checks

## Idempotence and Recovery

The workflow file is declarative. Pushing it multiple times is safe. If CI fails on the first run, fix the issues locally and push again.

## Interfaces and Dependencies

New files:
- `.github/workflows/ci.yml`

Dev dependencies (CI-only):
- `pytest`, `pytest-cov` (already from plan 004)
- `ruff` (Python linter)
- `bandit` (Python security scanner)

No changes to production code.


Active plan:
- `genesis/plans/001-master-plan.md`

Active spec:
- `genesis/SPEC.md`

Mapping notes:
- composite plan mapped from plan structure; humans may refine the checked-in contract later

Open tasks:
- Create GitHub Actions workflow for Python tests
- Add linting step (ruff or flake8)
- Add security scan step (bandit or safety)
- Add the no-hashing audit as a CI step
- Configure branch protection for main
- Verify pipeline runs green on current codebase

Artifacts to write:
- `spec.md`
- `review.md`
