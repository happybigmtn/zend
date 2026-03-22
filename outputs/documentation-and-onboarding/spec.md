# Documentation & Onboarding — Spec

**Status:** Complete
**Lane:** documentation-and-onboarding
**Date:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice for the documentation frontier. After
this work, a new contributor can go from cloning the repo to running the full
Zend system in under 10 minutes, following only the documentation.

## Deliverables

### Core Documentation

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | 130 | Gateway doc — what is Zend, quickstart, architecture, links |
| `docs/contributor-guide.md` | 220 | Dev setup, project structure, making changes, submitting PRs |
| `docs/operator-quickstart.md` | 200 | Home hardware deployment, systemd setup, recovery |
| `docs/api-reference.md` | 300 | All daemon endpoints, CLI commands, error codes |
| `docs/architecture.md` | 350 | System diagrams, module explanations, design decisions |

### Required Artifacts

| File | Purpose |
|------|---------|
| `outputs/documentation-and-onboarding/spec.md` | This spec |
| `outputs/documentation-and-onboarding/review.md` | Review findings |

## Scope

### Included

- README rewrite with quickstart and architecture overview
- Contributor guide with dev setup instructions
- Operator quickstart for home hardware deployment
- API reference with all endpoints documented
- Architecture document with system diagrams and module explanations

### Excluded

- Tutorial videos or screencasts
- Interactive sandbox environment
- Hosted documentation site
- Multi-language translations

## Progress

- [x] Read and understand all input documents (README.md, SPEC.md, SPECS.md, PLANS.md, DESIGN.md, genesis/plans/001-master-plan.md)
- [x] Read and understand the actual implementation (daemon.py, cli.py, store.py, spine.py, scripts, apps)
- [x] Rewrite README.md with quickstart and architecture overview
- [x] Create docs/contributor-guide.md with dev setup instructions
- [x] Create docs/operator-quickstart.md for home hardware deployment
- [x] Create docs/api-reference.md with all endpoints documented
- [x] Create docs/architecture.md with system diagrams and module explanations
- [x] Create outputs/documentation-and-onboarding/spec.md
- [x] Create outputs/documentation-and-onboarding/review.md

## Acceptance Criteria

| Criterion | Verification |
|-----------|--------------|
| README under 200 lines | Line count < 200 |
| Quickstart works | `./scripts/bootstrap_home_miner.sh` succeeds |
| Contributor guide covers setup | Read guide, follow steps, run tests |
| Operator guide covers recovery | Reset state, re-bootstrap, verify works |
| API reference matches code | Verify each endpoint exists in daemon.py |
| Architecture doc accurate | Read code, verify module descriptions correct |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| README is gateway, not manual | Long READMEs get skimmed. Details go in docs/ |
| Docs live in docs/ directory | Docs travel with code. No wiki drift. |
| Stdlib-only language | No external dependencies for docs. |
| Single-file command center preserved | No build step. Opens directly in browser. |
