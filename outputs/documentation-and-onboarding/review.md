# Documentation & Onboarding — Review

Status: In Progress

## Summary

This review covers the documentation artifacts created for Zend milestone 1. The goal is to verify documentation accuracy by following it on a clean machine and ensuring all documented commands work as described.

## Artifacts Under Review

| Artifact | Path | Status |
|---|---|---|
| README | `README.md` (rewrite) | Pending |
| Contributor Guide | `docs/contributor-guide.md` | Pending |
| Operator Quickstart | `docs/operator-quickstart.md` | Pending |
| API Reference | `docs/api-reference.md` | Pending |
| Architecture | `docs/architecture.md` | Pending |

## Review Checklist

### README.md Rewrite

- [ ] One-paragraph description present and accurate
- [ ] Quickstart has exactly 5 commands
- [ ] Commands are in correct order (clone, bootstrap, open HTML, status, control)
- [ ] Architecture diagram is ASCII and matches `genesis/SPEC.md`
- [ ] Directory structure is current and complete
- [ ] Links to docs/, specs/, plans/, references/ work
- [ ] Prerequisites list Python 3.10+ and no other deps
- [ ] Running tests command is correct
- [ ] Total lines under 200

### Contributor Guide

- [ ] Dev environment setup covers Python version, venv, pytest
- [ ] Running locally section explains bootstrap, daemon, client, all scripts
- [ ] Project structure section explains each directory and why
- [ ] Making changes section covers edit, run tests, verify
- [ ] Coding conventions mention stdlib-only, naming, error handling
- [ ] Plan-driven development section explains ExecPlans
- [ ] Submitting changes covers branch naming, PR template, CI checks
- [ ] A new contributor can follow this guide end-to-end

### Operator Quickstart

- [ ] Hardware requirements are realistic (any Linux box with Python 3.10+)
- [ ] Installation section shows clone and no pip install
- [ ] Configuration section documents all environment variables
- [ ] First boot walkthrough matches bootstrap script output
- [ ] Pairing a phone step-by-step matches pair script behavior
- [ ] Opening command center explains how to access index.html
- [ ] Daily operations covers status, mode change, events
- [ ] Recovery section covers state corruption and daemon restart
- [ ] Security notes cover LAN-only binding

### API Reference

- [ ] All endpoints documented: /health, /status, /miner/start, /miner/stop, /miner/set_mode
- [ ] Each endpoint has method and path
- [ ] Each endpoint has authentication requirement
- [ ] Each endpoint has request body (if applicable)
- [ ] Each endpoint has response format with example JSON
- [ ] Each endpoint has error responses with codes
- [ ] Each endpoint has working curl example

### Architecture Document

- [ ] System overview has ASCII diagram of all components
- [ ] Module guide covers daemon.py: purpose, key functions, state
- [ ] Module guide covers cli.py: purpose, key functions, state
- [ ] Module guide covers spine.py: purpose, key functions, state
- [ ] Module guide covers store.py: purpose, key functions, state
- [ ] Data flow section traces command from client → daemon → spine → response
- [ ] Auth model explains pairing, capabilities, tokens
- [ ] Event spine section explains append, query, routing
- [ ] Design decisions section explains stdlib-only, LAN-only, JSONL, single HTML

## Verification Steps

### Step 1: Fresh Clone Test

```bash
# Clone repository
git clone <repo-url> && cd zend

# Verify README quickstart works
./scripts/bootstrap_home_miner.sh
# Expected: Daemon starts, principal bootstrapped, pairing bundle shown

# Verify daemon health
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}

# Verify CLI status
python3 services/home-miner-daemon/cli.py status
# Expected: JSON with status, mode, hashrate, etc.
```

### Step 2: Contributor Guide Test

```bash
# Create virtual environment
python3 -m venv venv && source venv/bin/activate

# Install pytest
pip install pytest

# Run tests
python3 -m pytest services/home-miner-daemon/ -v
# Expected: All tests pass
```

### Step 3: Operator Quickstart Test

```bash
# On fresh Linux machine (or VM)
# Install Python 3.10+
python3 --version

# Clone and bootstrap
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh

# Pair a device
./scripts/pair_gateway_client.sh --client my-phone

# View status
python3 services/home-miner-daemon/cli.py status --client my-phone

# Control miner
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

### Step 4: API Reference Test

```bash
# Start daemon
./scripts/bootstrap_home_miner.sh --daemon

# Test each endpoint
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
curl -X POST http://127.0.0.1:8080/miner/start
curl -X POST http://127.0.0.1:8080/miner/stop
curl -X POST -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}' \
  http://127.0.0.1:8080/miner/set_mode
```

### Step 5: Architecture Verification

Read `docs/architecture.md` and verify against actual code:
- Do the module descriptions match the actual implementation?
- Are the function signatures correct?
- Does the data flow diagram match the actual request path?
- Are the design decision rationales accurate?

## Issues Found

(To be updated during review.)

## Recommendations

(To be updated during review.)

## Final Assessment

(To be updated after all checks pass.)
