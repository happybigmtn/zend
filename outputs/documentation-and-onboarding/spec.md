# Documentation & Onboarding — Specification

**Status:** Complete
**Generated:** 2026-03-22

## Overview

This document specifies the documentation deliverables for the Zend project, covering README, contributor guide, operator quickstart, API reference, and architecture documentation.

## Scope

### Documentation Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| README | `README.md` | Gateway document with quickstart |
| Contributor Guide | `docs/contributor-guide.md` | Dev setup and conventions |
| Operator Quickstart | `docs/operator-quickstart.md` | Home hardware deployment |
| API Reference | `docs/api-reference.md` | All daemon endpoints |
| Architecture | `docs/architecture.md` | System diagrams and modules |

### Requirements

1. **Self-contained:** All docs must be understandable without external references
2. **Verifiable:** Every command must work against the codebase
3. **Beginner-friendly:** New contributors can follow without prior knowledge
4. **Accurate:** Code examples must match actual implementation

## Milestones

### Milestone 1: README Rewrite

**Deliverable:** `README.md` under 200 lines

**Content:**
- One-paragraph description
- Quickstart (5 commands)
- ASCII architecture diagram
- Directory structure
- Links to deep-dive docs
- Prerequisites (Python 3.10+)
- Running tests

**Acceptance:** Reader can follow quickstart from fresh clone and see daemon health return `{"status": "ok"}`

### Milestone 2: Contributor Guide

**Deliverable:** `docs/contributor-guide.md`

**Content:**
- Dev environment setup (Python, venv)
- Running locally (bootstrap, daemon, client)
- Project structure (each directory explained)
- Making changes (edit, test, verify)
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development (ExecPlan format)
- Design system (pointer to DESIGN.md)
- Submitting changes (branch naming, PR template)

**Acceptance:** New contributor can set up environment and run test suite by following only this guide.

### Milestone 3: Operator Quickstart

**Deliverable:** `docs/operator-quickstart.md`

**Content:**
- Hardware requirements (any Linux, Python 3.10+)
- Installation (clone, no pip)
- Configuration (environment variables)
- First boot walkthrough
- Pairing phone step-by-step
- Opening command center
- Daily operations (status, mode, events)
- Recovery (state corruption, daemon won't start)
- Security (LAN-only, what to check)

**Acceptance:** Follow guide on Raspberry Pi, daemon starts, phone pairs, status renders.

### Milestone 4: API Reference

**Deliverable:** `docs/api-reference.md`

**Content:**
- Method and path for each endpoint
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example for each endpoint

**Endpoints:**
- `GET /health`
- `GET /status`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

**Acceptance:** Every curl example works against running daemon and produces documented output.

### Milestone 5: Architecture Document

**Deliverable:** `docs/architecture.md`

**Content:**
- System overview with ASCII diagram
- Module guide (purpose, functions, state)
- Data flow (command path from client to spine)
- Auth model (PrincipalId, capabilities, pairing)
- Event spine (append/query/routing)
- Design decisions (why stdlib, LAN-only, JSONL, HTML)

**Acceptance:** New engineer can read this and accurately predict how a new endpoint would be implemented.

## Technical Details

### Architecture

```
Documentation Layer
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│                         Docs                                   │
│  README.md ──► Quickstart                                      │
│     │                                                         │
│     └──► docs/                                                │
│              ├── contributor-guide.md                          │
│              ├── operator-quickstart.md                        │
│              ├── api-reference.md                              │
│              └── architecture.md                               │
└───────────────────────────────────────────────────────────────┘
```

### Dependencies

None. Documentation is pure Markdown with embedded diagrams.

## Acceptance Criteria

- [x] README.md under 200 lines, includes quickstart
- [x] Contributor guide enables test suite execution
- [x] Operator guide covers full deployment lifecycle
- [x] API reference curl examples work against daemon
- [x] Architecture doc correctly describes current system
- [x] All docs self-contained (no broken links)

## Implementation Notes

### README Structure

1. Brief description (what, who, key claims)
2. Quickstart code block (5 commands)
3. Architecture ASCII diagram
4. Component table
5. Running tests
6. Prerequisites
7. Environment variables table
8. Scripts table
9. Directory structure
10. Links to deep-dive docs

### API Reference Format

For each endpoint:
```markdown
### METHOD /path

Description...

**Request:**
```
TYPE /path
[Headers]

{JSON body}
```

**Response:**
```json
{
  "field": "description"
}
```

**curl Example:**
```bash
curl ...
```

### Architecture Diagrams

Use ASCII art for system diagrams:

```text
Client ──► Daemon ──► Store/Spine
              │
              └──► Miner
```

## Risks

| Risk | Mitigation |
|------|------------|
| Docs drift from code | CI job to run quickstart commands |
| API examples stale | Include curl commands that can be scripted |
| Operator assumes network | Document minimum requirements and troubleshoot |

## Out of Scope

- Video tutorials
- Interactive documentation site
- Translated versions
- Search functionality
