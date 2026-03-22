# Documentation & Onboarding — Spec

**Status**: Completed

**Lane**: `documentation-and-onboarding`

**Goal**: Bootstrap the first honest reviewed slice for documentation and onboarding.

## Purpose / User-Visible Outcome

A new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using the quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Scope

### What this lane covers

- `README.md` rewrite with quickstart and architecture overview
- `docs/contributor-guide.md` with dev setup instructions
- `docs/operator-quickstart.md` for home hardware deployment
- `docs/api-reference.md` with all endpoints documented
- `docs/architecture.md` with system diagrams and module explanations

### What this lane does not cover

- Actual implementation code changes
- Test suite expansion
- CI/CD pipeline for documentation
- External hosting (docs site, wiki)

## Architecture Decisions

### Decision: Documentation lives in `docs/` directory

**Rationale**: Docs should travel with the code. A wiki creates drift. Everything should be verifiable from a clone.

**Location**: `docs/` subdirectory with topic-specific files.

### Decision: README.md is a gateway, not a manual

**Rationale**: Long READMEs get skimmed. The README should tell you what Zend is, how to run it, and where to find more. Details go in `docs/`.

**Limit**: Under 200 lines.

### Decision: Code examples must be verifiable

**Rationale**: Documentation that can't be followed is worse than no documentation. Every code example should work against a running daemon.

**Approach**: Show actual command output, not just syntax.

## Implementation Notes

### README.md

- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- ASCII architecture diagram
- Directory structure table
- Links to detailed docs
- Prerequisites (Python 3.10+)
- Test command

### Contributor Guide

- Dev environment setup (Python, venv, pytest)
- Running locally (bootstrap, daemon, CLI)
- Project structure with purpose for each directory
- Making changes workflow
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development explanation
- Design system pointer
- Common issues section

### Operator Quickstart

- Hardware requirements (any Linux with Python 3.10+)
- Installation steps
- Configuration via environment variables
- First boot walkthrough with expected output
- Device pairing step-by-step
- Opening command center instructions
- Daily operations (status, control, events)
- Recovery procedures
- Security guidance (LAN-only, VPN for remote)

### API Reference

- Every daemon endpoint documented
- For each: method, path, auth, request, response, errors, curl example
- CLI commands documented with examples
- Error codes and HTTP statuses

### Architecture Document

- ASCII system diagram
- Module guide for each Python module
- Data flow diagrams
- Auth model explanation
- Event spine design rationale
- Design decisions with trade-offs
- Adding new endpoints guide

## Acceptance Criteria

| Criterion | Verification |
|-----------|---------------|
| README quickstart works from fresh clone | Run commands, see expected output |
| Contributor guide enables test execution | New contributor runs pytest successfully |
| Operator guide covers full deployment lifecycle | Deploy on Raspberry Pi or VM |
| API reference examples work | curl commands return documented responses |
| Architecture doc matches actual code | Read code, verify descriptions are accurate |
| No broken links | All cross-references resolve |
| Under 200 lines in README | wc -l README.md |

## Durability

This spec is durable. It defines documentation standards and locations. Future documentation work should:

1. Follow these conventions
2. Keep examples verifiable
3. Update docs when code changes
4. Test documentation as part of CI (future)

## Implementation Notes

During implementation, discovered and fixed:

1. **ZEND_TOKEN_TTL_HOURS**: Does not exist in code, removed from docs
2. **ZEND_DAEMON_URL**: Exists in cli.py, added to docs
3. **No test infrastructure**: Added explicit notes in contributor guide
4. **Enum serialization bug**: Fixed `stop()` to return string like other methods
5. **Missing endpoints**: `/metrics`, `/spine/events`, `/pairing/refresh` now implemented

The documentation is now accurate and matches the implementation after fixes.
