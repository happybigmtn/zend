# Documentation & Onboarding — Spec

**Status:** Completed
**Date:** 2026-03-22
**Lane:** documentation-and-onboarding

## Purpose

Bootstrap the first honest reviewed slice for documentation and onboarding. After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation.

## Scope

### Outputs Created

1. **README.md** (rewritten)
   - One-paragraph description
   - 5-command quickstart
   - ASCII architecture diagram
   - Directory structure
   - Prerequisites
   - Links to detailed docs

2. **docs/architecture.md** (new)
   - System overview diagram
   - Module guide for each Python module
   - Data flow diagrams
   - Auth model explanation
   - Design decisions with rationale

3. **docs/api-reference.md** (new)
   - All daemon endpoints documented
   - Request/response examples with curl commands
   - CLI reference with all commands
   - Environment variables
   - Error handling

4. **docs/contributor-guide.md** (new)
   - Dev environment setup
   - Running locally
   - Project structure
   - Making changes
   - Coding conventions
   - Design system reference
   - Testing
   - Submitting changes

5. **docs/operator-quickstart.md** (new)
   - Hardware requirements
   - Installation steps
   - Configuration
   - First boot walkthrough
   - Pairing a phone
   - Daily operations
   - Recovery procedures
   - Security guidance

## Key Design Decisions

### Documentation Location

**Decision:** Documentation lives in `docs/` directory, not wiki or external site.

**Rationale:** Docs should travel with the code. A wiki creates drift. Everything should be verifiable from a clone.

### README as Gateway

**Decision:** README.md is a gateway, not a manual. It should be under 200 lines.

**Rationale:** Long READMEs get skimmed. The README should tell you what Zend is, how to run it, and where to find more. Details go in `docs/`.

### stdlib-Only Code

**Decision:** Milestone 1 uses Python standard library only.

**Rationale:** No pip dependencies to manage, easier deployment on restricted systems, smaller attack surface. Milestone 1 focuses on contract, not features.

### LAN-Only Phase 1

**Decision:** Daemon binds to LAN-only interface in milestone 1.

**Rationale:** Lowest blast radius for first deployment. Proves the control-plane thesis without internet exposure.

## Acceptance Criteria

- [x] README.md under 200 lines with quickstart and architecture overview
- [x] docs/architecture.md with system diagrams and module explanations
- [x] docs/api-reference.md with all endpoints and curl examples
- [x] docs/contributor-guide.md with dev setup and coding conventions
- [x] docs/operator-quickstart.md for home hardware deployment
- [x] All documentation verifiable by reading and following from a fresh clone

## Verification

### Quickstart Verification

```bash
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
python3 services/home-miner-daemon/cli.py status --client alice-phone
# Open apps/zend-home-gateway/index.html in browser
```

**Expected:** Daemon returns `{"healthy": true}` and status shows `stopped` with `paused` mode.

### Documentation Accuracy

Each document was written by reading the actual source code:
- `daemon.py` — All endpoints verified
- `cli.py` — All commands verified
- `spine.py` — Event kinds and schemas verified
- `store.py` — Principal and pairing contract verified
- `index.html` — UI components and API calls verified

## Non-Goals

- CI verification of quickstart commands (deferred to plan 005)
- Interactive tutorials
- Video walkthroughs
- Translated documentation

## Files Modified

| File | Action |
|------|--------|
| `README.md` | Rewritten |
| `docs/architecture.md` | Created |
| `docs/api-reference.md` | Created |
| `docs/contributor-guide.md` | Created |
| `docs/operator-quickstart.md` | Created |

## Files Created

- `outputs/documentation-and-onboarding/spec.md` (this file)
- `outputs/documentation-and-onboarding/review.md` (review artifact)
