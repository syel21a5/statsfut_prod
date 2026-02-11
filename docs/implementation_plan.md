# Plan: Optimize API Usage for Professional 24/7 Operation

## Problem Analysis

Current configuration polls APIs every 15 seconds, consuming approximately **23,040 requests/day**, which exceeds the available **8,200 requests/day** limit.

## Proposed Solution: Smart Dynamic Polling

### Strategy Overview

Instead of polling every 15 seconds regardless of match activity, implement **intelligent conditional polling** that adapts based on:
1. Whether there are actually live matches happening
2. Time of day (matches are more common in evenings)
3. Database state (check local DB first before hitting API)

---

## Proposed Changes

### 1. Optimized Polling Intervals

#### Current Intervals
```python
LIVE_UPDATE_INTERVAL = 15  # Too aggressive
FULL_SYNC_INTERVAL = 3600  # OK
```

#### New Smart Intervals
```python
# When NO live matches detected
IDLE_CHECK_INTERVAL = 300  # 5 minutes (288 requests/day)

# When live matches ARE happening
ACTIVE_UPDATE_INTERVAL = 60  # 1 minute (1,440 requests/day during active periods)

# Full sync (results + upcoming)
FULL_SYNC_INTERVAL = 3600  # 1 hour (480 requests/day)
```

### 2. Database-First Strategy

Before calling the API, check the local database:
- If no matches are scheduled in the next 30 minutes → use IDLE mode
- If matches are live or starting soon → use ACTIVE mode

This reduces API calls by **~80%** during off-peak hours.

### 3. Time-Based Intelligence

```python
# Peak hours (14:00-23:00 local time) → More frequent checks
# Off-peak hours (00:00-13:59) → Reduced frequency
```

### 4. Estimated Daily Consumption

**Scenario: 4 hours of live matches per day**

| Activity | Interval | Requests/Day |
|----------|----------|--------------|
| Idle checks (20h) | 5 min | 240 |
| Active updates (4h) | 1 min | 240 |
| Full syncs | 1 hour | 480 |
| **TOTAL** | | **960** ✅ |

**Safety margin: 8,200 - 960 = 7,240 requests remaining**

---

## Implementation Files

### [MODIFY] [run_live_updates.py](file:///c:/Users/PCPE/Documents/sites/statsfut2.statsfut.com/run_live_updates.py)

Add smart polling logic:
- Check database for upcoming/live matches before API call
- Dynamic interval adjustment based on match state
- Time-based intelligence for peak/off-peak hours

### [NEW] systemd Service Configuration

Create `/etc/systemd/system/statsfut-live.service` to run the script as a professional background service that auto-restarts on failure and server reboot.

---

## Verification Plan

### Automated Tests
1. Monitor API usage via Django cache
2. Add logging to track interval changes
3. Verify service runs continuously for 24 hours

### Manual Verification
1. Check logs show dynamic interval switching
2. Verify live matches update within 1-2 minutes
3. Confirm total daily API usage stays under 2,000 requests
