merge_ready: no
manual_proof_pending: no
reason: The live proof run still exposes a contract regression where the embedded fallback emits `MinerStatus.*` and `MinerMode.*` instead of the specified lowercase snapshot values, and the current no-local-hashing audit is too weak to count as sufficient proof for this slice.
next_action: Normalize the fallback and daemon JSON serialization to the documented `MinerSnapshot` wire values, add automated coverage for the script-visible status output and the no-local-hashing guarantee, then rerun the verification gate.
