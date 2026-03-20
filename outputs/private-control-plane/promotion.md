merge_ready: no
manual_proof_pending: no
reason: quality.md is green, but the recorded verification is undermined by stale daemon startup failures and artifact drift that leave the real slice proof unreliable.
next_action: fix the daemon bootstrap verification path so stale pid or port conflicts cannot masquerade as success, then rerun verification and refresh the artifacts from that clean proof.
