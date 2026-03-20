merge_ready: yes
manual_proof_pending: no
reason: `quality.md` is clean, the changed CLI/bootstrap handoff is re-proved locally, and the unchanged adapter HTTP path is already covered by the earlier successful bootstrap gate in the lane record.
next_action: Merge this slice, and rerun `./scripts/bootstrap_hermes.sh` in a socket-enabled environment if you want a fresh end-to-end record for this exact commit.
