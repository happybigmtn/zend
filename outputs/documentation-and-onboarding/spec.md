# Documentation & Onboarding — Specification

**Status:** Complete
**Date:** 2026-03-22
**Lane:** documentation-and-onboarding

## Purpose

This specification defines the documentation artifacts required to enable:
1. New contributors to set up and run the Zend system
2. Operators to deploy on home hardware
3. Developers to understand and extend the API
4. Stakeholders to understand the system architecture

## Scope

### Required Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| README.md | repo root | Quickstart and overview |
| contributor-guide.md | docs/ | Dev setup and conventions |
| operator-quickstart.md | docs/ | Home hardware deployment |
| api-reference.md | docs/ | Daemon API endpoints |
| architecture.md | docs/ | System design and modules |

### Excluded from Scope

- Wiki or external documentation site (docs travel with code)
- Video tutorials
- Interactive demos
- Translated documentation

## Documentation Standards

### README.md Requirements

- Under 200 lines
- Quickstart in 5 commands
- Architecture diagram (ASCII)
- Directory structure
- Links to deeper documentation
- Prerequisites listed
- Test command included

### Contributor Guide Requirements

- Dev environment setup (Python 3.10+)
- Running locally (bootstrap, daemon, client)
- Project structure with rationale
- Making changes workflow
- Coding conventions (stdlib-only)
- Plan-driven development explanation
- Design system reference
- Submitting changes (branch, PR)

### Operator Quickstart Requirements

- Hardware requirements
- Installation steps
- Configuration (environment variables)
- First boot walkthrough
- Pairing a phone
- Opening command center
- Daily operations
- Recovery procedures
- Security notes

### API Reference Requirements

For each endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example
- Error responses with codes
- curl example

### Architecture Document Requirements

- System overview diagram
- Module guide (purpose, functions, state)
- Data flow diagrams
- Auth model explanation
- Event spine documentation
- Design decision rationale

## Verification Criteria

1. **README.md**: A reader can follow the quickstart from a fresh clone and see the daemon health check return `{"status": "ok"}`
2. **Contributor Guide**: A contributor who has never seen the repo can set up their environment and run the test suite by following only this document
3. **Operator Quickstart**: Follow the guide on a Raspberry Pi or similar Linux box; daemon starts, phone pairs, status renders in browser
4. **API Reference**: Every curl example in the document works against a running daemon and produces the documented output
5. **Architecture Document**: A new engineer can read this document and accurately predict how a new endpoint would be implemented

## Dependencies

- Python 3.10+ standard library
- HTTP server (stdlib http.server)
- JSON handling (stdlib json)

## Constraints

- All documentation must be self-contained (no external links required for basic understanding)
- All curl examples must be verifiable against a running daemon
- All file paths must be repository-relative
- No external services required for basic operation
