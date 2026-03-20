merge_ready: no
manual_proof_pending: yes
reason: Quality is green and the focused Hermes status proofs pass, but the required bootstrap gate cannot complete in this sandbox because the daemon cannot bind its local socket.
next_action: Re-run `./scripts/bootstrap_hermes.sh` on a host that permits local socket binding and confirm `./scripts/hermes_status.sh` reports a healthy daemon before promoting this slice.
