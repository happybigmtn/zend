# Error Taxonomy

**Status:** Contract for Milestone 1
**Last Updated:** 2026-03-19

## Error Classes

### PairingTokenExpired

**Code:** `PAIRING_TOKEN_EXPIRED`
**Context:** The pairing token has exceeded its validity window.
**User Message:** "This pairing request has expired. Please request a new one from your Zend Home."
**Rescue Action:** Reject pairing, request new token via bootstrap.

### PairingTokenReplay

**Code:** `PAIRING_TOKEN_REPLAY`
**Context:** A pairing token was reused that has already been consumed.
**User Message:** "This pairing request has already been used."
**Rescue Action:** Reject pairing, log audit event, request new token.

### GatewayUnauthorized

**Code:** `GATEWAY_UNAUTHORIZED`
**Context:** The gateway client lacks the required capability for the requested action.
**User Message:** "You don't have permission to perform this action. Request control capability from your Zend Home."
**Rescue Action:** Reject action, surface capability request.

### GatewayUnavailable

**Code:** `GATEWAY_UNAVAILABLE`
**Context:** The Zend Home gateway is not reachable.
**User Message:** "Unable to connect to Zend Home. Check that it's powered on and on the same network."
**Rescue Action:** Return explicit unavailable state, suggest recovery.

### MinerSnapshotStale

**Code:** `MINER_SNAPSHOT_STALE`
**Context:** The cached miner status is older than the freshness threshold.
**User Message:** "Showing cached status. Zend Home may be offline."
**Rescue Action:** Return stale flag and warning, do not present as fresh.

### ControlCommandConflict

**Code:** `CONTROL_COMMAND_CONFLICT`
**Context:** Two competing control requests are in-flight.
**User Message:** "Another control action is in progress. Please try again."
**Rescue Action:** Reject or queue deterministically, clear conflict state.

### EventAppendFailed

**Code:** `EVENT_APPEND_FAILED`
**Context:** Failed to write event to the encrypted event spine.
**User Message:** "Unable to save this operation. Please try again."
**Rescue Action:** Retry append, surface failure if persistent.

### LocalHashingDetected

**Code:** `LOCAL_HASHING_DETECTED`
**Context:** The gateway client process shows evidence of hashing work.
**User Message:** "Security warning: unexpected mining activity detected."
**Rescue Action:** Fail audit non-zero, log detailed evidence.

### InvalidPrincipalId

**Code:** `INVALID_PRINCIPAL_ID`
**Context:** The principal identifier is malformed or unknown.
**User Message:** "Account not recognized."
**Rescue Action:** Request re-authentication or bootstrap.

### HermesUnauthorized

**Code:** `HERMES_UNAUTHORIZED`
**Context:** The Hermes agent lacks the required capability for the requested action.
**User Message:** "Hermes does not have permission to perform this action."
**Rescue Action:** Reject action, log attempt.

### HermesUnknown

**Code:** `HERMES_UNKNOWN`
**Context:** The Hermes agent ID is not recognized as a paired agent.
**User Message:** "Unknown Hermes agent. Pair via the Hermes pairing flow first."
**Rescue Action:** Reject request, return 401.

### DaemonPortInUse

**Code:** `DAEMON_PORT_IN_USE`
**Context:** The gateway daemon cannot bind to its configured port.
**User Message:** "Zend Home is already running or port is in use."
**Rescue Action:** Exit with context and recovery hint.
