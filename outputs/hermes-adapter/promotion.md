merge_ready: no
manual_proof_pending: no
reason: The delegated Hermes slice is implemented and offline adapter proofs pass, but the required bootstrap gate cannot be re-proved in this sandbox because local socket creation is blocked.
next_action: Re-run ./scripts/bootstrap_hermes.sh and a live read_status() check in an environment that permits binding the local daemon socket.
