merge_ready: no
manual_proof_pending: yes
reason: quality.md is green, but the required proof gate could not be reproduced in this sandbox and the slice still has contract drift in its idempotent pairing and HTTP surface artifacts.
next_action: Fix the capability-array and event/status contract mismatches, then rerun `./scripts/bootstrap_home_miner.sh` plus the endpoint checks in a bind-capable environment and refresh the verification artifacts.
