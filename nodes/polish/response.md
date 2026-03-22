Both durable artifacts are polished. Here's a summary of the changes made:

**`spec.md` — Structural and clarity polish**
- Added a `Lane` header for supervisory-plane orientation
- Converted the "What was built" prose into a proper table-based reference for each function (name, description, behavior)
- Added a dedicated "Token format" section with explicit JSON example and a note about the JWT swap-in point
- Added a "Bug fixed at implementation time" section to make it self-contained
- Moved the boundaries table above validation evidence for faster scanning
- Added explicit remaining-task bullets

**`review.md` — Repo-specificity and honest documentation**
- Added a `Lane` header for consistency with spec
- Replaced generic "slice" framing language with project-specific terminology
- Added the "Token format / JWT swap-in point" observation as a concrete refactoring note
- Added gap #5 for the `HermesConnection` construction duplication — a real refactoring opportunity
- Tightened the "Risk assessment" to be specific about what the pre-check does
- Kept all T-code evidence intact
- Honest gaps are now numbered for traceability