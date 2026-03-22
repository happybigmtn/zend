# Documentation & Onboarding — Spec

**Lane:** documentation-and-onboarding
**Status:** REVISE (pending correctness fixes from review)
**Date:** 2026-03-22

---

## Purpose

Provide documentation that lets three audiences succeed without tribal knowledge:

1. **Contributors** — clone, run tests, make changes, submit code
2. **Operators** — deploy the daemon on home hardware, pair a phone, operate daily
3. **Reviewers/Auditors** — understand the architecture, auth model, and data flow

## Scope

Five documents were produced:

| Document | Audience | Source of Truth |
|---|---|---|
| `README.md` | All | Quickstart, architecture overview, directory map |
| `docs/contributor-guide.md` | Contributors | Dev setup, conventions, plan-driven workflow |
| `docs/operator-quickstart.md` | Operators | Hardware deploy, systemd, pairing, recovery |
| `docs/api-reference.md` | Contributors + Operators | Every daemon endpoint with curl examples |
| `docs/architecture.md` | All | System diagrams, module guide, auth model, design decisions |

## Acceptance Criteria

1. A contributor can follow `docs/contributor-guide.md` from clone to passing test suite without asking questions
2. An operator can follow `docs/operator-quickstart.md` from bare hardware to a paired phone showing miner status
3. Every endpoint documented in `docs/api-reference.md` exists in `daemon.py` and returns the documented response shape
4. Every CLI subcommand documented in any doc file exists in `cli.py` with the documented flags
5. The README quickstart (5 steps) completes without error on a clean clone
6. No document claims a capability that the code does not implement (e.g., encryption, token enforcement)

## Current Status

Criteria 1 and 2 are partially met (docs exist, structure is sound, but specific commands fail).
Criteria 3, 4, 5, and 6 all fail — see `outputs/documentation-and-onboarding/review.md` for details.

## Blocking Issues (from review)

1. Three phantom API endpoints documented but not implemented
2. One phantom CLI subcommand documented but not wired
3. README quickstart step 5 fails (observe-only client can't control)
4. `.env` sourcing pattern doesn't export to child processes
5. "Encrypted" label on plaintext event journal
6. Duplicate `scripts/` block in README
7. CORS limitation undocumented
8. Daemon's lack of HTTP-level auth not called out in operator guide

## Remaining Work

After the blocking issues are fixed, the lane needs one more pass:

- Run the README quickstart on a clean clone (no prior state/) and verify all 5 steps produce the documented output
- Run the operator-quickstart on a fresh Linux environment and verify systemd startup through status read
- Verify every curl example in api-reference.md against a running daemon
- Grep all doc files for CLI subcommand references and confirm each exists in cli.py's argparse
