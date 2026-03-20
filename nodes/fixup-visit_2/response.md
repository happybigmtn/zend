All verification scripts pass.

`★ Insight ─────────────────────────────────────`
- **Configuration drift bug**: The daemon respected `ZEND_BIND_PORT` but the CLI hardcoded port 8080. This is a common testing/CI bug where components drift apart over time.
- **Centralized config pattern**: Both daemon and CLI should read from the same env vars. The fix was adding `ZEND_BIND_HOST`/`ZEND_BIND_PORT` to CLI's URL construction.
`─────────────────────────────────────────────────`

**Fixup complete.** The issue was a port mismatch between the daemon (using `ZEND_BIND_PORT=18080`) and the CLI (hardcoded to port 8080). Fixed `cli.py` to read `ZEND_BIND_HOST` and `ZEND_BIND_PORT` environment variables, matching the daemon's configuration.