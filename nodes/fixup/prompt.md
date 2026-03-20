Goal: Implement the next approved `hermes-adapter:hermes-adapter` slice.

Inputs:
- `agent-adapter.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `hermes-adapter:hermes-adapter`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
./scripts/bootstrap_hermes.sh
true`
  - Stdout: (empty)
  - Stderr:
    ```
    /bin/bash: line 2: ./scripts/bootstrap_hermes.sh: No such file or directory
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 3.6m tokens in / 29.7k out
  - Files: outputs/hermes-adapter/agent-adapter.md, outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/review.md, outputs/hermes-adapter/verification.md, scripts/hermes_summary_smoke.sh, services/hermes-adapter/__init__.py, services/hermes-adapter/adapter.py, services/hermes-adapter/auth_token.py, services/hermes-adapter/errors.py, services/hermes-adapter/models.py, services/hermes-adapter/tests/__init__.py, services/hermes-adapter/tests/test_hermes_adapter.py
- **verify**: fail
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout: (empty)
  - Stderr:
    ```
    /bin/bash: line 2: ./scripts/bootstrap_hermes.sh: No such file or directory
    ```

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## stderr /bin/bash: line <n>: ./scripts/bootstrap_hermes.sh: no such file or directory


# Hermes Adapter Implementation Lane — Fixup

Fix only the current slice for `hermes-adapter-implement`.

Current Slice Contract:
Inspect the relevant repo surfaces, preserve existing doctrine, and produce the lane artifacts honestly.


Verification artifact must cover
- summarize the automated proof commands that ran and their outcomes

Priorities:
- unblock the active slice's first proof gate
- stay within the named slice and touched surfaces
- preserve setup constraints before expanding implementation scope
- keep implementation and verification artifacts durable and specific
- do not create or rewrite `promotion.md` during Fixup; that file is owned by the Settle stage
- do not hand-author `quality.md`; the Quality Gate rewrites it after verification
