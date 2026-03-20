merge_ready: no
manual_proof_pending: no
reason: The required proof gate failed in this stage and the required implementation and verification artifacts are missing, so the reviewed evidence does not fully match the repo state.
next_action: Add `outputs/hermes-adapter/implementation.md` and `outputs/hermes-adapter/verification.md`, then rerun `./scripts/bootstrap_hermes.sh` in an environment that permits the daemon to bind to `127.0.0.1:8080` before re-settling promotion.
