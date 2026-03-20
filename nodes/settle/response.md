Wrote the promotion verdict to [promotion.md](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/outputs/private-control-plane/promotion.md): `merge_ready: no`.

The blockers I verified were:

- On March 20, 2026, rerunning `./scripts/bootstrap_home_miner.sh` failed in this environment with `PermissionError: [Errno 1] Operation not permitted` while binding `127.0.0.1:8080`, so the required first proof gate was not reproducible.
- [scripts/pair_gateway_client.sh](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/scripts/pair_gateway_client.sh#L61) emits malformed idempotent JSON for multi-capability devices: `["observe,control"]` instead of `["observe","control"]`.
- [references/event-spine.md](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/references/event-spine.md#L46) requires `pairing_token` in `pairing_granted`, but [services/home-miner-daemon/spine.py](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/services/home-miner-daemon/spine.py#L107) omits it; [services/home-miner-daemon/daemon.py](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/services/home-miner-daemon/daemon.py#L184) also omits `version` from `/spine/events`.
- [verification.md](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/outputs/private-control-plane/verification.md#L34) contains an invalid command example, `--balanced`, which doesn’t match [set_mining_mode.sh](/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/scripts/set_mining_mode.sh).

I left source code unchanged in this stage and only settled promotion truthfully.