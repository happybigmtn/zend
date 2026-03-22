Both artifacts are polished. Here's what changed and why:

**`spec.md` — rewritten as a true spec, not a plan rehash**

- Added a **"What the user can/cannot yet do"** block to make the current capability boundary immediately legible to a supervisor
- Tightened the daemon API table with an explicit note that auth is not enforced — avoids the spec implying a trust guarantee it doesn't deliver
- Added a **Design System Alignment** section with the actual required palette and a note about the current warm-stone divergence
- Added an **Acceptance Criteria table** with current status (✅/❌) so progress is scannable
- Trimmed everything that belongs in the ExecPlan (step-by-step instructions, error registry, test diagram, recovery sequences)

**`review.md` — rewritten as a focused supervisory artifact**

- Elevated the five **graduation blockers** to the top instead of burying them in a 300-line audit
- Kept the critical/high/medium severity framing from the Nemesis pass
- Removed duplication of plan mechanics (the ExecPlan is the authoritative source for mechanics)
- Added a **"What the slice does well"** section to give the implementers credit for the structural work
- Added a **Repo Path Notes** section to document the output-path discrepancy finding
- Kept the 18 should-fix items as a numbered table for clean tracking

The two documents now have distinct purposes: the spec describes the target state, the review assesses the current gap and what must change to close it.