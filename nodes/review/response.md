`★ Insight ─────────────────────────────────────`
**Why unsigned tokens are worse than no tokens:** The base64 authority token creates a false sense of security. Code reviewers and future contributors will see `connect()` "validating" a token and assume the boundary is enforced. In reality, the token is just a structured sticky-note — anyone can write one. This is more dangerous than having no auth at all, because it suppresses the alarm that would otherwise prompt someone to add real auth. A signed token (HMAC at minimum) turns the sticky-note into a sealed envelope — the daemon becomes the only entity that can issue valid tokens.

**The double-body-read pattern** is a classic `BaseHTTPRequestHandler` trap. The request body (`self.rfile`) is a stream, not a buffer. Once `read()` consumes it, it's gone. The fix is to parse the body once in `do_POST()` and thread it through to sub-handlers via parameter or instance variable.
`─────────────────────────────────────────────────`

---

**Bottom line:** The specify stage produced correct architectural shapes — the capability constants, event allowlist, and adapter function signatures are all right. But the generated code has two crash-on-first-call bugs (timedelta import, double body read) that make 19/22 tests fail, the authority model is unsigned (security facade), and the CLI integration doesn't pass auth headers. The review artifacts are written to `outputs/hermes-adapter-implementation/`.

**To unblock:** Fix B1 + B2 first (10 minutes, gets tests green), then address S1 + S2 (real auth) before calling this a trust boundary.