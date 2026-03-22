Both artifacts are polished. Here's a summary of the key changes made:

## spec.md — Changes from Draft

1. **Fixed plan path** — Removed reference to non-existent `genesis/plans/008-documentation-and-onboarding.md`. Correct path is `plans/2026-03-19-build-zend-home-command-center.md`.

2. **Corrected attribution** — The original attributed `--client my-phone` errors to the plan's quickstart, but the plan's Concrete Steps actually use `alice-phone` correctly. The errors originate in the plan's *documentation milestone descriptions*, not in its quickstart.

3. **Added `fetch_upstreams.sh` status** — Script is working but requires `upstream/manifest.lock.json` which doesn't exist yet (blocker noted).

4. **Added `no_local_hashing_audit.sh` always-passes note** — The daemon simulates rather than hashes, so the audit always exits 0.

5. **Clarified `ZEND_DAEMON_URL`** — Not read by the daemon; CLI-only.

6. **Added pairing-store full-rewrite note** — Relevant for operator recovery docs.

7. **Structured the deliverables section** with clear must/must-not lists per document.

## review.md — Changes from Draft

1. **Verdict changed from "BLOCKED" to "CONDITIONALLY READY"** — The plan's Concrete Steps are correct. Only the documentation milestones (milestones 4–5) contain phantom references.

2. **Reorganized blockers** into "Must Fix" (errors in deliverables) and "Should Fix" (honesty improvements), with a "Nice to Have" tail.

3. **Strengthened security findings** with exact code line references (`daemon.py:168-200`, `store.py:86-89`, etc.).

4. **Added "What Can Ship Today"** — Clear statement that all 5 docs can be written immediately using the corrected ground truth, with no code changes needed.

5. **Removed incorrect "wrong quickstart" finding** — The plan does not use `my-phone`; that was a misattribution.

6. **Added Finding 6** — Event spine has no size bound (relevant for ops docs).