**Findings**
- High: state is split between repo-level [scripts/bootstrap_home_miner.sh](/tmp/zend-private-control-2-1773982813/worktree/scripts/bootstrap_home_miner.sh#L19) and cwd-relative [store.py](/tmp/zend-private-control-2-1773982813/worktree/services/home-miner-daemon/store.py#L19) / [spine.py](/tmp/zend-private-control-2-1773982813/worktree/services/home-miner-daemon/spine.py#L17), so the current recovery story is not honest yet.
- High: `observe` is documented but not enforced on read paths in [read_miner_status.sh](/tmp/zend-private-control-2-1773982813/worktree/scripts/read_miner_status.sh#L34), [cli.py](/tmp/zend-private-control-2-1773982813/worktree/services/home-miner-daemon/cli.py#L45), and the gateway UI hard-codes capabilities in [index.html](/tmp/zend-private-control-2-1773982813/worktree/apps/zend-home-gateway/index.html#L620).
- High: the event spine is append-only but not private yet, because [spine.py](/tmp/zend-private-control-2-1773982813/worktree/services/home-miner-daemon/spine.py#L56) writes plaintext payloads to disk.

**Artifacts**
- Reviewed contract: [control-plane-contract.md](/tmp/zend-private-control-2-1773982813/worktree/outputs/private-control-plane/control-plane-contract.md)
- Honest review: [review.md](/tmp/zend-private-control-2-1773982813/worktree/outputs/private-control-plane/review.md)

The contract locks the milestone 1 boundary around one shared `PrincipalId`, capability-scoped pairing records, one private event spine, and an operations inbox that is only a projection of that spine. The review calls out the real implementation gains already present, plus the remaining blockers before this can honestly count as a finished private-control-plane proof.

**Validation**
- Confirmed locally: pairing with `observe` and `observe,control`, observe-only control denial, and Hermes summary append into the same spine.
- Could not fully validate live HTTP flows here because `./scripts/bootstrap_home_miner.sh` failed to bind `127.0.0.1:8080` in this sandbox with `PermissionError: [Errno 1] Operation not permitted`.