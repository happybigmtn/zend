merge_ready: no
manual_proof_pending: no
reason: The required proof gate is not currently reliable enough for merge because `./scripts/bootstrap_hermes.sh` failed here when daemon startup hit `PermissionError: [Errno 1] Operation not permitted`, and the reviewed `agent-adapter.md` source artifact is also missing from `outputs/hermes-adapter`.
next_action: Re-run `./scripts/bootstrap_hermes.sh` in an environment where the daemon can already run or bind successfully and restore or confirm the reviewed `outputs/hermes-adapter/agent-adapter.md` contract before promoting this slice.
