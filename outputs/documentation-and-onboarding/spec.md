# Documentation & Onboarding — Specification

**Status:** Completed
**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-22

## Purpose

This specification defines the documentation deliverables for the Zend project to enable:
1. A new contributor to go from clone to working system in under 10 minutes
2. An operator to deploy Zend on home hardware without external assistance
3. API consumers to integrate with the daemon programmatically
4. Engineers to understand the system architecture for future development

## Deliverables

### 1. README.md (Rewrite)

**Goal:** Gateway document under 200 lines explaining what Zend is and how to run it.

**Acceptance Criteria:**
- [x] One-paragraph description of Zend
- [x] Quickstart: 5 commands from clone to working system
- [x] ASCII architecture diagram
- [x] Directory structure overview
- [x] Prerequisites list
- [x] Running tests command
- [x] Links to detailed docs

**Location:** `README.md`

### 2. docs/contributor-guide.md (New)

**Goal:** Enable a contributor to set up their environment and run tests without tribal knowledge.

**Acceptance Criteria:**
- [x] Dev environment setup (Python, venv, pytest)
- [x] Running locally (bootstrap, daemon, client, scripts)
- [x] Project structure with module explanations
- [x] Making changes workflow
- [x] Coding conventions (stdlib-only, naming, error handling)
- [x] Plan-driven development explanation
- [x] Design system reference
- [x] Common tasks and troubleshooting

**Location:** `docs/contributor-guide.md`

### 3. docs/operator-quickstart.md (New)

**Goal:** Enable an operator to deploy Zend on home hardware (Raspberry Pi, old laptop, etc.).

**Acceptance Criteria:**
- [x] Hardware requirements
- [x] Installation steps
- [x] Configuration (environment variables)
- [x] First boot walkthrough
- [x] Pairing a phone step-by-step
- [x] Daily operations
- [x] Recovery procedures
- [x] Security checklist
- [x] Troubleshooting table

**Location:** `docs/operator-quickstart.md`

### 4. docs/api-reference.md (New)

**Goal:** Document every daemon endpoint with request/response examples.

**Acceptance Criteria:**
- [x] GET /health
- [x] GET /status
- [x] POST /miner/start
- [x] POST /miner/stop
- [x] POST /miner/set_mode
- [x] Event spine query via CLI
- [x] All endpoints have curl examples
- [x] Error responses documented

**Location:** `docs/api-reference.md`

### 5. docs/architecture.md (New)

**Goal:** Explain system architecture with diagrams and module guide.

**Acceptance Criteria:**
- [x] System overview diagram
- [x] Module-by-module guide
- [x] Data flow explanation
- [x] Auth model description
- [x] Design decisions with rationale
- [x] Glossary of terms

**Location:** `docs/architecture.md`

## Verification

Documentation accuracy verified by:

1. **Quickstart Verification:** All commands in README quickstart tested against running daemon
2. **Architecture Accuracy:** Module descriptions verified against source code
3. **API Completeness:** All endpoints from `daemon.py` documented
4. **Cross-Reference:** All docs link to each other appropriately

## Non-Goals

This spec does not include:
- Installation instructions for non-Linux platforms (limited scope)
- Detailed Zcash integration docs (future phase)
- Security hardening beyond LAN-only defaults
- Multi-daemon deployment

## Dependencies

No code changes required. Documentation is additive.

## Files Created/Modified

| File | Action |
|------|--------|
| `README.md` | Rewritten |
| `docs/contributor-guide.md` | Created |
| `docs/operator-quickstart.md` | Created |
| `docs/api-reference.md` | Created |
| `docs/architecture.md` | Created |
| `outputs/documentation-and-onboarding/spec.md` | Created (this file) |
| `outputs/documentation-and-onboarding/review.md` | Created (review artifact) |
