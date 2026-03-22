# Genesis Plan 006: Token Enforcement

**Status:** Pending
**Priority:** High
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Enforce token replay prevention as defined in the error taxonomy. Currently, `store.py` sets `token_used=False` but no code path sets it to `True`.

## Problem

```python
# store.py
pairing = GatewayPairing(
    ...
    token_used=False  # Always False, never set to True
)
```

This means a pairing token can be replayed indefinitely.

## Solution

1. Track token usage in the pairing store
2. Mark token as used after successful pairing
3. Reject subsequent pair attempts with same token
4. Implement token expiration check

## Concrete Steps

1. Modify `create_pairing_token()` to return unique token
2. Add `use_pairing_token(token)` function
3. Modify `pair_client()` to mark token as used
4. Add check in pairing flow to reject used tokens
5. Add test for token replay prevention

## Expected Outcome

- Used tokens rejected with `PairingTokenReplay` error
- Token expiration enforced
- Audit log captures replay attempts
