# Documentation & Onboarding — Spec

**Lane:** `documentation-and-onboarding`
**Status:** Complete
**Date:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice of documentation for Zend. After this
work, a new contributor can go from cloning the repo to running the full system
in under 10 minutes, following only the documentation.

## Scope

### Documents Created/Modified

| Document | Type | Audience | Purpose |
|----------|------|----------|---------|
| `README.md` | Modified | All | Gateway: what is Zend, quickstart, directory structure |
| `docs/contributor-guide.md` | New | Developers | Dev environment setup, running locally, making changes |
| `docs/operator-quickstart.md` | New | Operators | Home hardware deployment, configuration, daily ops |
| `docs/api-reference.md` | New | API consumers | All endpoints with curl examples |
| `docs/architecture.md` | New | Engineers | System diagrams, module explanations, data flow |

### Quality Standards Applied

1. **Self-contained**: Each document can be followed without external references
2. **Verifiable**: Commands have expected outputs shown
3. **Accessible**: Clear language, no jargon without definition
4. **Consistent**: Same terminology used across all documents

## Document Specifications

### README.md

- Under 200 lines
- One-paragraph description
- Quickstart (5 commands)
- ASCII architecture diagram
- Directory structure with descriptions
- Links to deep-dive documentation
- Prerequisites listed
- Test command included

### Contributor Guide

- Python version and venv setup
- Running locally (bootstrap, CLI, HTML client)
- Project structure explanation
- Making changes workflow
- Coding conventions (stdlib-only, error handling, module structure)
- Plan-driven development explanation
- Design system reference
- Recovery procedures

### Operator Quickstart

- Hardware requirements (any Linux with Python 3.10+)
- Installation (clone, no pip needed)
- Environment variable configuration
- First boot walkthrough with expected output
- Phone pairing step-by-step
- Command center access instructions
- Daily operations (status, mode, events)
- Recovery procedures
- Security checklist (LAN-only, firewall)

### API Reference

- Every daemon endpoint documented
- Method and path
- Request format
- Response format with example JSON
- Error responses with codes
- curl examples for each endpoint
- CLI commands documented

### Architecture Document

- System overview with ASCII diagram
- Module guide (daemon.py, cli.py, spine.py, store.py)
- Key functions and state for each module
- Data flow diagrams
- Auth model explanation
- Event spine design rationale
- Design decisions with rationale
- Extension points

## Validation

All documentation verified by:

1. Running quickstart commands from README
2. Following contributor guide setup steps
3. Executing API reference curl examples
4. Verifying architecture matches actual code

## Decisions Made

1. **README is gateway, not manual**: Under 200 lines, links to deep-dive docs
2. **Docs travel with code**: No external wiki or hosted docs
3. **Stdlib-only enforced**: All code examples use only stdlib
4. **LAN-only default**: Security section emphasizes local network only
5. **HTML client noted**: Command center requires API_BASE update for network access

## Known Limitations

- HTML client defaults to localhost; remote access requires manual config
- No automated doc testing (manual verification only)
- Systemd service is example; actual deployment may vary
- Python 3.10+ required; older versions not supported

## Artifacts Produced

- `README.md` — rewritten with quickstart
- `docs/contributor-guide.md` — dev setup guide
- `docs/operator-quickstart.md` — deployment guide
- `docs/api-reference.md` — API documentation
- `docs/architecture.md` — system design document
- `outputs/documentation-and-onboarding/spec.md` — this file
- `outputs/documentation-and-onboarding/review.md` — review results
