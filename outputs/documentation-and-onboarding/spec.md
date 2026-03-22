# Documentation & Onboarding — Spec

**Status:** Complete
**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-22
**Author:** Genesis Sprint

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes by following only the documentation. An
operator can deploy the daemon on home hardware using the quickstart guide. The
API is documented with curl examples. The architecture is explained with
diagrams. No tribal knowledge is required.

## Scope

This spec covers the complete first-documentation slice for Zend:

1. **README.md** (rewrite) — One-paragraph description, 5-command quickstart,
   ASCII architecture diagram, directory structure, links to deep-dive docs,
   prerequisites, test command. Under 200 lines.

2. **docs/contributor-guide.md** — Dev environment setup (Python 3.10+,
   pytest), running locally (bootstrap, daemon, client, all scripts), project
   structure (every file and directory explained), making changes (stdlib-only
   convention, event spine rules, testing, scripts pattern), plan-driven
   development (ExecPlans reference), design system (DESIGN.md pointer), and
   submitting changes.

3. **docs/operator-quickstart.md** — Hardware requirements (any Linux box,
   Python 3.10+), installation (git clone, no pip), configuration (all env
   vars documented), first boot (expected output for every step), pairing a
   phone (file URL and HTTP server methods), daily operations (status/start/
   stop/mode/-events), recovery (port conflict, state corrupt, phone can't
   connect, unauthorized), and security notes (LAN-only default, what not to
   expose, hardening checklist).

4. **docs/api-reference.md** — Every daemon endpoint documented: method, path,
   auth requirement, request format, response format with example JSON, error
   responses with codes, curl example. Covers all HTTP endpoints (`/health`,
   `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`) and the full
   CLI reference. Notes on auth model and token-based auth deferral.

5. **docs/architecture.md** — ASCII system diagram, module guide (daemon.py,
   cli.py, store.py, spine.py), data flow (control command and pairing flows),
   auth model (two-layer: daemon no-auth, CLI capability check), event spine
   routing table, design decisions with rationale (stdlib-only, LAN-only,
   JSONL not SQLite, single HTML file, observe/control capabilities).

6. **Verification** — Bootstrap, status, pairing, and control commands tested
   against the running daemon. All curl examples confirmed working.

## Acceptance Criteria

- [x] README.md is under 200 lines and includes the 5-command quickstart
- [x] README.md includes an ASCII architecture diagram matching `genesis/SPEC.md`
- [x] README.md links to all four new docs files
- [x] Contributor guide enables test suite execution without tribal knowledge
- [x] Operator quickstart covers full deployment lifecycle on home hardware
- [x] API reference includes a curl example for every endpoint
- [x] Architecture doc explains every module and decision
- [x] All documentation verified against the actual codebase (no stale commands)

## What Was Created

```
README.md                          (rewritten, 3696 bytes)
docs/contributor-guide.md          (new, 7993 bytes)
docs/operator-quickstart.md        (new, 6165 bytes)
docs/api-reference.md              (new, 7378 bytes)
docs/architecture.md              (new, 11980 bytes)
```

## What Was Not in Scope

- CI job that runs quickstart commands automatically (deferred to plan 005)
- Dark mode expansion for the command center
- Token expiry enforcement in the daemon
- Remote internet access documentation
- Multi-device sync documentation

## Artifacts

This spec is the durable record of what the documentation-and-onboarding lane
delivered. The companion `review.md` contains the review findings.
