## Documentation & Onboarding — Complete

### What was created

**`README.md`** (189 lines, under 200 as required)
- One-paragraph description of Zend
- 5-command quickstart from clone to working system
- ASCII architecture diagram
- Directory structure table
- Links to all deep-dive docs
- Prerequisites and test commands

**`docs/contributor-guide.md`** (266 lines)
- Dev environment setup with verified bootstrap workflow
- Module-by-module project structure guide
- Making changes workflow (read contract → edit → verify → test)
- Coding conventions (stdlib-only, naming, error handling, thread safety)
- Plan-driven development guidance
- Design system alignment
- Submission guidelines

**`docs/operator-quickstart.md`** (393 lines)
- Hardware requirements table (min/recommended)
- Step-by-step installation and first boot walkthrough
- LAN binding configuration with security notes
- Phone pairing walkthrough with capability reference
- Command center opening instructions
- Daily operations (all scripts documented)
- Recovery procedures (port conflict, state corruption, network issues)
- Security notes (LAN-only, capability model, plaintext spine)

**`docs/api-reference.md`** (463 lines)
- All daemon endpoints with curl examples and verified responses
- Full CLI reference for all 6 subcommands
- Event kinds table
- Error codes reference
- Environment variable documentation

**`docs/architecture.md`** (354 lines)
- ASCII system overview diagram
- Module guide for daemon.py, store.py, spine.py, cli.py
- Control command and pairing flow diagrams
- Auth model (PrincipalId, Pairing, Capabilities)
- Event spine routing table
- Six design decision rationales

**`outputs/documentation-and-onboarding/spec.md`** — spec artifact
**`outputs/documentation-and-onboarding/review.md`** — review artifact

### Bug found and fixed

`services/home-miner-daemon/daemon.py` was returning enum string representations
(`"MinerStatus.STOPPED"`) instead of lowercase values (`"stopped"`) due to
Python's `json.dumps()` not auto-calling `.value` on Enum instances. Fixed in all
four return sites. Verified working after fix.