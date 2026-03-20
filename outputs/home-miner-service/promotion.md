merge_ready: no
manual_proof_pending: yes
reason: Fresh promotion proof is not sufficient because `./scripts/bootstrap_home_miner.sh` now fails in this sandbox with `PermissionError: [Errno 1] Operation not permitted` during socket creation and the reviewed `service-contract.md` and `review.md` artifacts are missing from `outputs/home-miner-service`.
next_action: Restore the reviewed contract artifacts and rerun `./scripts/bootstrap_home_miner.sh` plus the preserved HTTP proof commands in an environment that permits local socket creation before promoting this slice.
