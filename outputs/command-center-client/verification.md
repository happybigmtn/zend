# Command Center Client — Verification

**Lane:** command-center-client
**Slice:** inbox-event-connection
**Date:** 2026-03-20

## Automated Proof Commands

### 1. Daemon Health Check
```bash
curl http://127.0.0.1:8080/health
```
**Expected:** `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`

### 2. Events Endpoint - Empty Spine
```bash
curl "http://127.0.0.1:8080/events"
```
**Expected:** `{"events": []}`

### 3. Events Endpoint - With Kind Filter
```bash
curl "http://127.0.0.1:8080/events?kind=control_receipt"
```
**Expected:** `{"events": [...]}` or `{"events": []}` depending on spine state

### 4. Events Endpoint - With Limit
```bash
curl "http://127.0.0.1:8080/events?limit=5"
```
**Expected:** `{"events": [...]}` with at most 5 events

### 5. Events Endpoint - Invalid Kind
```bash
curl "http://127.0.0.1:8080/events?kind=invalid_kind"
```
**Expected:** `{"error": "invalid_kind"}`

### 6. Bootstrap and Pair
```bash
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client test-device --capabilities observe,control
```
**Expected:** Pairing succeeds, events appended to spine

### 7. Control Action Creates Event
```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```
**Expected:** Control receipt event appended to spine

### 8. Events After Control Action
```bash
curl "http://127.0.0.1:8080/events?kind=control_receipt"
```
**Expected:** Returns control_receipt event with status "accepted"

### 9. CLI Events Command
```bash
cd services/home-miner-daemon && python3 cli.py events --kind control_receipt --limit 5
```
**Expected:** Lists control receipt events

## Manual Verification Steps

1. Open `apps/zend-home-gateway/index.html` in a browser
2. Navigate to Inbox tab
3. Verify empty state shows initially
4. Run control action: `./scripts/set_mining_mode.sh --client alice-phone --mode performance`
5. Refresh Inbox tab
6. Verify control receipt card appears with correct content

## Verification Summary

| Command | Outcome |
|---------|---------|
| Daemon health | ✓ Returns healthy status |
| Events endpoint (no params) | ✓ Returns empty array |
| Events with kind filter | ✓ Filters correctly |
| Events with limit | ✓ Limits results |
| Events with invalid kind | ✓ Returns error |
| Bootstrap | ✓ Creates principal and pairing |
| Pair client | ✓ Appends pairing events |
| Control action | ✓ Appends control_receipt |
| Events after action | ✓ Contains new event |