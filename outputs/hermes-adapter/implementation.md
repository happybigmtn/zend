# Hermes Adapter — Implementation

**Status:** Package-Surface Slice Complete
**Generated:** 2026-03-20

## Slice Summary

This slice makes the reviewed `hermes_adapter` package surface executable without widening the milestone 1 boundary. The service remains rooted in `services/hermes-adapter/`, and a new importable facade under `services/hermes-adapter/hermes_adapter/` now exposes the documented adapter, model, error, and token-helper imports.

## What Changed

### Importable Package Facade

- Added `services/hermes-adapter/hermes_adapter/` wrappers for `adapter`, `auth_token`, `errors`, `models`, and `token`.
- Exported the reviewed root-package symbols: `HermesAdapter`, `HermesConnection`, `HermesSummary`, `MinerSnapshot`, and `make_summary_text`.
- Kept the service layout unchanged so the existing bootstrap and smoke flows still target the owned Hermes adapter surface.

### Token Helper Surface

- Kept `services/hermes-adapter/auth_token.py` as the implementation module for token creation, validation, and replay protection.
- Added `hermes_adapter.token` as the reviewed token-helper import path.
- Avoided adding a top-level `services/hermes-adapter/token.py` file because that filename shadows Python's stdlib `token` module when the service directory is on `sys.path`.

### Verification-Oriented Updates

- Reworked `services/hermes-adapter/tests/test_hermes_adapter.py` to import the real `hermes_adapter` package instead of constructing a synthetic package with `importlib`.
- Added package-surface coverage for `from hermes_adapter import ...` and `from hermes_adapter.token import ...`.
- Added a positive `appendSummary()` proof that verifies the latest `hermes_summary` event lands in the spine.
- Updated `scripts/hermes_summary_smoke.sh` to use the reviewed package surface and confirm the appended summary matches the latest spine event.

## Touched Surfaces

- `services/hermes-adapter/__init__.py`
- `services/hermes-adapter/hermes_adapter/__init__.py`
- `services/hermes-adapter/hermes_adapter/adapter.py`
- `services/hermes-adapter/hermes_adapter/auth_token.py`
- `services/hermes-adapter/hermes_adapter/errors.py`
- `services/hermes-adapter/hermes_adapter/models.py`
- `services/hermes-adapter/hermes_adapter/token.py`
- `services/hermes-adapter/tests/test_hermes_adapter.py`
- `scripts/hermes_summary_smoke.sh`

## Result

- The reviewed `hermes_adapter` imports now execute in the repo.
- The smoke proof now validates the spine write instead of ending with a static success echo.
- Milestone 1 authority boundaries remain unchanged: observe and summarize only, with no direct control surface added.
