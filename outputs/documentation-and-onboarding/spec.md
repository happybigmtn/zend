# Documentation & Onboarding — Lane Spec

**Lane:** `documentation-and-onboarding`
**Produced by:** specify + review pipeline
**Date:** 2026-03-22

---

## Purpose

Bootstrap a reviewed, accurate documentation slice for the Zend project. Every document must be verifiable: a new contributor or operator following the docs on a clean machine should reach a working system without guessing.

---

## Scope

### What This Lane Covers

| Artifact | Type | Status |
|---|---|---|
| `README.md` | Entry point | ✅ Already complete (reviewed) |
| `docs/architecture.md` | System diagrams + module explanations | ✅ Already complete (reviewed) |
| `docs/contributor-guide.md` | Dev setup, coding conventions, making changes | 🆕 Created this lane |
| `docs/operator-quickstart.md` | Home hardware deployment on Raspberry Pi | 🆕 Created this lane |
| `docs/api-reference.md` | All daemon HTTP endpoints with examples | 🆕 Created this lane |

### Acceptance Criteria

1. **Quickstart is reproducible.** A new clone, running the 5 quickstart steps, reaches a working command center without errors.
2. **Contributor guide is self-contained.** No external links required for dev setup. All file paths are repo-relative. Every CLI command shown is copy-paste runnable.
3. **Operator quickstart is hardware-specific.** Targets Raspberry Pi. Covers systemd service setup, LAN IP configuration, and mobile browser access via static file serving.
4. **API reference is complete.** All daemon endpoints documented with request/response shapes, error codes, and `curl`/CLI examples.
5. **Architecture doc is accurate.** Module responsibilities, data flow diagrams, and design decisions match the current source code.
6. **All docs are consistent.** Same terminology, same command syntax, same file paths throughout. No stale references.

---

## Durables

### `outputs/documentation-and-onboarding/spec.md`

This file. Captures lane scope, acceptance criteria, and the artifact inventory.

### `outputs/documentation-and-onboarding/review.md`

Review artifact. Records what was checked, what passed, what failed, and what was corrected during the review pass.

---

## Constraints

- No external dependencies beyond what the project already requires (Python 3.10 stdlib, Bash)
- No build step for any doc; all are plain Markdown
- No stale paths — all file locations verified against the current tree
- No hypothetical features — all documented behavior exists in the current codebase

---

## Verification Plan

After writing each doc, the reviewer:
1. Reads the doc against the source code it describes
2. Runs the quickstart steps from a clean state
3. Follows the operator quickstart steps mentally (target platform permitting)
4. Cross-references API reference with `daemon.py` routes and `cli.py` subparsers
5. Checks all file paths exist in the current tree
6. Notes discrepancies in `review.md`

---

## Open Questions

- Should the operator quickstart cover real miner hardware integration, or only the simulator? **Decision: simulator only for milestone 1.**
- Is there a preferred method for serving the HTML gateway on mobile? **Decision: `python3 -m http.server` is the recommended approach; `file://` navigation is also documented.**
