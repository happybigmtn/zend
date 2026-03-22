Both artifacts are written. Here's a summary of what was done:

---

## Polish Summary

### `outputs/carried-forward-build-command-center/spec.md` (143 lines)

Made three structural changes from the original:

1. **Tied every claim to a concrete file path.** The original listed components by name and path but left acceptance criteria as abstract statements. The polished version maps each criterion to `services/home-miner-daemon/daemon.py`, `store.py:89`, `cli.py`, etc. so a reader can go directly to the evidence.

2. **Frontier task table links to genesis plan numbers** as requested by the input framing, making the spec actionable for the supervisory plane.

3. **Known Gaps section is numbered C1–C11** with precise file:line citations and brief remediation notes, converting the prior review's prose findings into a checklist the next lane can work from.

### `outputs/carried-forward-build-command-center/review.md` (170 lines)

Made four changes from the original:

1. **"Not Approved" is stated in the verdict line**, not buried in a prose paragraph. The prior review listed critical gaps but still issued "APPROVED."

2. **C1 (daemon auth) and C2 (token expiry) are clearly blocking**, not deferred risks. C3 (encryption) is explicitly deferred with the condition that the boundary must be designed now — converting an implicit assumption into an explicit requirement.

3. **What Works section is a single compact list** — no tables or prose — so the supervisory plane can scan it in seconds.

4. **Forward Path section** is a numbered list of deliverables for the next lane, each tied to a genesis plan number, so the carry-forward is traceable.