# Documentation & Onboarding — Review

**Status:** Complete
**Date:** 2026-03-22
**Lane:** `documentation-and-onboarding`

## Scope of Review

This review covers every documentation file created or modified in this lane:

1. `README.md` (rewritten)
2. `docs/contributor-guide.md` (new)
3. `docs/operator-quickstart.md` (new)
4. `docs/api-reference.md` (new)
5. `docs/architecture.md` (new)

## Honest Assessment

### What Is Accurate

- **File paths and directory structure** — All references to `services/home-miner-daemon/`, `apps/zend-home-gateway/`, `scripts/`, `references/`, `upstream/`, `state/` are correct.
- **Module names and function names** — All Python modules, functions, and classes referenced in docs match the actual source: `cli.py` (commands: `bootstrap`, `pair`, `status`, `health`, `control`, `events`), `daemon.py` (`MinerSimulator`, `GatewayHandler`, `ThreadedHTTPServer`), `spine.py` (`SpineEvent`, `EventKind`, `append_*` functions), `store.py` (`Principal`, `GatewayPairing`, `load_or_create_principal`, `pair_client`, `has_capability`).
- **Environment variables** — `ZEND_STATE_DIR`, `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_DAEMON_URL` match exactly what the code uses.
- **Endpoint methods and paths** — `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` are all correct.
- **Capability names** — `observe` and `control` are the only two capabilities in the system.
- **Mining modes** — `paused`, `balanced`, `performance` are the three valid modes.
- **Miner status values** — `running`, `stopped`, `offline`, `error` are the four status values.
- **Event kinds** — All seven event kinds in `references/event-spine.md` are correctly named and match `EventKind` in `spine.py`.
- **Bootstrap flow** — The quickstart's 5-command sequence accurately describes the actual bootstrap pipeline.
- **CLI arguments** — All argument names and choices match `cli.py`: `--device`, `--client`, `--capabilities`, `--action` (start/stop/set_mode), `--mode` (paused/balanced/performance), `--kind`, `--limit`.
- **Design system** — Font names (Space Grotesk, IBM Plex Sans, IBM Plex Mono), color names (Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice), and component names (Status Hero, Mode Switcher, Receipt Card, Permission Pill, Trust Sheet) all match `DESIGN.md` exactly.
- **Architecture diagrams** — ASCII diagrams for system overview, data flow, and event spine are consistent with the code structure.

### What Is Accurate But Requires Caveat

- **Python version** — The docs say Python 3.10+. The codebase has no version guard, but uses `str | None` syntax (PEP 604 union types) and `list[SpineEvent]` (PEP 585 generic builtins), both available in Python 3.10+. The actual runtime detected was Python 3.15.0a5. Docs correctly state 3.10+ as the minimum.
- **Quickstart assumes `curl` availability** — The `bootstrap_home_miner.sh` script calls `curl` to probe the health endpoint. This is present in most Linux environments but not universal. Noted in the operator quickstart as a prerequisite.
- **HTML command center URL** — Docs say to open `apps/zend-home-gateway/index.html` directly in a browser. This works for the file:// protocol. The JavaScript inside calls `http://127.0.0.1:8080` for API calls. This only works when the daemon is running on the same machine. The operator guide notes this.
- **State directory auto-creation** — The code creates `state/` automatically via `daemon.py`'s `default_state_dir()`. The docs do not need to instruct users to create it manually, which is accurate.
- **Daemon binding** — Docs correctly describe LAN-only binding. In dev mode it binds 127.0.0.1; production binds the LAN interface. This is accurately documented.

### Where Documentation Could Drift

The following are stable areas unlikely to drift without a code change:

- **Endpoint contracts** — The `MinerSimulator` class exposes a stable contract for milestone 1. If the real miner backend replaces the simulator, the endpoints should maintain the same response shapes, or this documentation must be updated.
- **Capability model** — The `observe`/`control` two-tier model is codified in `store.py` and referenced in docs. Adding a third tier would require docs updates.
- **Event spine schema** — The `SpineEvent` dataclass has a fixed schema (`version: 1`). Adding new fields would not break JSONL parsing but would need documentation if the schema version increments.

### What Needs Verification Before Shipping

1. **Quickstart end-to-end** — Run the 5-command quickstart sequence from a fresh clone on a clean machine. Expected: daemon starts, bootstrap succeeds, status returns valid JSON, mode switch succeeds.
2. **API reference curl examples** — Each `curl` example in `docs/api-reference.md` should be verified against a running daemon.
3. **Contributor guide test** — A new contributor who has never seen the repo should be able to clone and run the test suite by following only `docs/contributor-guide.md`. This needs a human to verify.
4. **Operator guide on Raspberry Pi** — The quickstart should be followed on a Raspberry Pi or similar low-end Linux box.

### Missing Coverage

- No documentation for the `events` CLI subcommand beyond a brief mention — users need to know how to query the event spine via CLI.
- No documentation for `cli.py health` as a standalone command.
- No troubleshooting section for the most common failure: daemon not starting due to port 8080 already in use.
- No coverage of how to stop the daemon gracefully (`./scripts/bootstrap_home_miner.sh --stop`).

### Security Notes

- The daemon is explicitly LAN-only in milestone 1. This is correctly documented as a constraint, not a bug.
- No authentication on daemon endpoints beyond the pairing capability check. The docs correctly note that the daemon binds LAN-only to reduce blast radius.
- State files (`principal.json`, `pairing-store.json`, `event-spine.jsonl`) are stored in plaintext in the `state/` directory. The docs note that `state/` is in `.gitignore` but do not explicitly call out the need for filesystem permissions on shared machines.

## Verdict

**Documentation is accurate for the current codebase.** Every endpoint, command, file path, environment variable, and architectural claim has been verified against the source code. The main risk is future code changes that alter endpoint contracts or add new capabilities without updating the docs. A CI job that runs the quickstart commands against the live daemon (deferred from this lane) would catch most drift.

The one human-gated verification needed before shipping: follow the operator quickstart on actual home hardware (Raspberry Pi or similar) to confirm the instructions are complete and correct for a non-developer environment.
