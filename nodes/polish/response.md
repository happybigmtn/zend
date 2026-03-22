Both durable artifacts are now in place at the required output path:

- **`outputs/hermes-adapter-implementation/spec.md`** — defines the Hermes adapter as a typed translation and validation layer between Hermes Gateway and the existing daemon/spine. Specifies `HermesConnection`, `HermesCapability` enum, `HermesPairing` store (under `hermes_pairings` key), token validation on every call, and the `user_message` event filter at the adapter layer. Includes 8 concrete acceptance criteria phrased as observable behavior.

- **`outputs/hermes-adapter-implementation/review.md`** — records the previous failure as a missing-artifacts deterministic failure, assesses the spec's strengths (correct architecture, clear outcomes, consistent code style) and four open questions that need addressing before implementation: token format, token presentation model, CLI entry point conventions, and test file naming. All four are captured as required fixes.

The key design decisions captured in `spec.md`:
1. Separate `hermes_pairings` store to avoid mixing capability vocabularies
2. Single `hermes.py` module (not a package) for simplicity at this stage
3. `user_message` filtering at the adapter layer preserves the shared spine contract
4. Token format follows existing `uuid.uuid4()` pattern from `store.py`