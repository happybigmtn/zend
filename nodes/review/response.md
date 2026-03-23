Review verdict: blocked.

Key findings:
- README quickstart is not executable as written. [README.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/README.md#L31) tells users to control `alice-phone`, but bootstrap only grants `observe` in [cli.py](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/services/home-miner-daemon/cli.py#L78).
- The home-hardware phone flow is broken. [operator-quickstart.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/docs/operator-quickstart.md#L164) says the UI will poll the daemon LAN IP automatically, but [index.html](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/apps/zend-home-gateway/index.html#L632) hard-codes `http://127.0.0.1:8080`.
- The API reference documents a nonexistent endpoint. [api-reference.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/docs/api-reference.md#L100) describes `GET /spine/events`, but [daemon.py](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/services/home-miner-daemon/daemon.py#L168) only serves `/health` and `/status` for GETs.
- One documented CLI path crashes. [contributor-guide.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/docs/contributor-guide.md#L160) recommends `events --kind`, but [cli.py](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/services/home-miner-daemon/cli.py#L190) passes a string into [spine.py](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/services/home-miner-daemon/spine.py#L87), which expects an enum and raises `AttributeError`.
- Token TTL/replay docs are ahead of the code. [operator-quickstart.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/docs/operator-quickstart.md#L363) documents 24h single-use tokens, but [store.py](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/services/home-miner-daemon/store.py#L40) does not persist a token value and does not read `ZEND_TOKEN_TTL_HOURS`.

I updated the durable artifacts to reflect the real review outcome:
- [spec.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/outputs/documentation-and-onboarding/spec.md)
- [review.md](/home/r/.fabro/runs/20260322-01KMBZZ22BXJM5WWSNMJMNC1DS/worktree/outputs/documentation-and-onboarding/review.md)

Verification I ran: fresh-state bootstrap, `status`, `pair`, `control`, `curl /health`, `curl /spine/events` (returned `404`), `events --kind` (crashed), and `python3 -m pytest services/home-miner-daemon/ -v` (collected `0` tests).