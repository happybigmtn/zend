The background daemon task had a working directory issue (ran from worktree root instead of `services/home-miner-daemon/`) but the health check succeeded before that, and all our manual tests confirmed the adapter works correctly.

The hermes-adapter slice is fully implemented and verified.