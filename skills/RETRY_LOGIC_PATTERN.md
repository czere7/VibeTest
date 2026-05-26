# Retry Logic Pattern - Multi-Tier Exponential Backoff with Cycle Recovery

## Overview
This pattern implements a robust two-tier retry mechanism designed for API calls that may experience transient failures, rate limits, or temporary service unavailability. It combines immediate retries with extended recovery periods.

## Pattern Structure

### Core Components
1. **Inner Retry Loop**: Fast retries for transient failures
2. **Outer Retry Cycle**: Extended recovery periods for persistent failures
3. **Progressive Delays**: Different wait times for different failure scenarios
4. **Comprehensive Logging**: Detailed tracking of retry attempts and cycles

## Implementation Details

### Configuration Parameters
```python
max_5min_retries = 6      # Number of outer retry cycles
inner_attempts = 5         # Number of immediate retries per cycle
short_delay = 3           # Seconds between inner retries
long_delay = 300          # Seconds (5 minutes) between outer cycles
```

### Logic Flow

```
┌─────────────────────────────────────────────────────────┐
│ Start Retry Cycle (retry_cycle = 0)                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ While retry_cycle < 6     │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Inner Loop: attempt 1-5   │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Try API Call              │
         └───────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ✓ Success              ✗ Exception
         │                       │
         │                       ▼
         │           ┌───────────────────────┐
         │           │ Log failure           │
         │           │ (attempt X/5)         │
         │           └───────────┬───────────┘
         │                       │
         │           ┌───────────┴──────────┐
         │           │                      │
         │      attempt < 5           attempt = 5
         │           │                      │
         │           ▼                      ▼
         │    ┌─────────────┐    ┌──────────────────┐
         │    │ Sleep 3s    │    │ retry_cycle++    │
         │    │ Continue    │    └────────┬─────────┘
         │    └─────────────┘             │
         │                      ┌─────────┴─────────┐
         │                      │                   │
         │              retry_cycle < 6    retry_cycle = 6
         │                      │                   │
         │                      ▼                   ▼
         │           ┌──────────────────┐  ┌───────────────┐
         │           │ Log 5min sleep   │  │ Log max retry │
         │           │ Sleep 300s       │  │ Return None   │
         │           │ Break inner loop │  └───────────────┘
         │           └────────┬─────────┘
         │                    │
         │                    └──────┐
         │                           │
         ▼                           ▼
    ┌────────────────────────────────────┐
    │ Return result / Restart outer loop │
    └────────────────────────────────────┘
```

### Pseudo-Code Template

```python
def api_call_with_retry(payload, config):
    """
    Robust API call with two-tier retry mechanism.
    
    Args:
        payload: Request payload
        config: Configuration dict with retry parameters
    
    Returns:
        API response or None if all retries exhausted
    """
    max_outer_cycles = config.get('max_cycles', 6)
    max_inner_attempts = config.get('max_attempts', 5)
    short_delay = config.get('short_delay', 3)
    long_delay = config.get('long_delay', 300)
    
    retry_cycle = 0
    
    # OUTER LOOP: Cycle through extended recovery periods
    while retry_cycle < max_outer_cycles:
        
        # INNER LOOP: Quick successive retries
        for attempt in range(1, max_inner_attempts + 1):
            try:
                # ATTEMPT: Make the actual API call
                response = make_api_call(payload)
                
                # SUCCESS: Return immediately
                return response
                
            except Exception as e:
                # LOG: Record the failure
                log_error(f"Attempt {attempt}/{max_inner_attempts}, "
                         f"Cycle {retry_cycle + 1}/{max_outer_cycles}: {e}")
                
                # DECISION POINT: Inner retry or outer cycle?
                if attempt < max_inner_attempts:
                    # Still have inner attempts left
                    time.sleep(short_delay)
                    continue  # Try again immediately (after short delay)
                else:
                    # All inner attempts exhausted
                    retry_cycle += 1
                    
                    if retry_cycle < max_outer_cycles:
                        # Start new cycle after long delay
                        log_info(f"All {max_inner_attempts} attempts failed. "
                                f"Sleeping {long_delay}s before cycle "
                                f"{retry_cycle}/{max_outer_cycles}")
                        time.sleep(long_delay)
                        break  # Exit inner loop to restart outer loop
                    else:
                        # All cycles exhausted
                        log_error(f"Maximum retry cycles ({max_outer_cycles}) "
                                 f"reached. Giving up.")
                        return None
    
    # Fallback: Should not reach here, but return None if we do
    return None
```

## Key Characteristics

### 1. **Two-Tier Retry Strategy**
- **Tier 1 (Inner)**: 5 quick attempts with 3-second delays
  - Handles transient network glitches
  - Fast recovery for temporary issues
  - Total time: ~15 seconds per cycle

- **Tier 2 (Outer)**: 6 extended cycles with 5-minute delays
  - Handles rate limiting
  - Allows service recovery time
  - Total time: Up to 30 minutes maximum

### 2. **Total Retry Capacity**
- Maximum attempts: 5 attempts × 6 cycles = **30 total attempts**
- Maximum wait time: (5 cycles × 5 minutes) + (30 attempts × 3 seconds) = **~25 minutes 90 seconds**
- Actual runtime: Varies based on when success occurs

### 3. **Failure Handling**
- **Immediate failures**: Caught and logged, retry after 3 seconds
- **Persistent failures**: After 5 attempts, trigger 5-minute cooldown
- **Complete failure**: After 6 cycles (30 attempts), return None

### 4. **Logging Strategy**
```python
# Log each attempt with context
print(f"{timestamp} Request failed (attempt {attempt}/5, "
      f"cycle {retry_cycle + 1}/{max_cycles}): {error}")

# Log cycle transitions
print(f"{timestamp} All 5 retry attempts failed. "
      f"Sleeping for 5 minutes before trying again "
      f"(cycle {retry_cycle}/{max_cycles})...")

# Log final failure
print(f"{timestamp} Maximum retry cycles ({max_cycles}) reached. "
      f"Giving up.")
```

## Application Guidelines

### When to Use This Pattern
✅ **Good for:**
- External API calls with rate limits
- Services with known temporary outages
- Critical operations that must eventually succeed
- Long-running batch processes
- Operations where eventual consistency is acceptable

❌ **Not suitable for:**
- Real-time user-facing operations (too slow)
- Operations requiring immediate feedback
- Non-idempotent operations without additional safeguards
- Systems with strict latency requirements

### Customization Points

1. **Adjust retry counts**:
   ```python
   max_inner_attempts = 3  # Fewer quick retries
   max_outer_cycles = 10   # More patience for recovery
   ```

2. **Modify delay timing**:
   ```python
   short_delay = 1        # Faster inner retries
   long_delay = 600       # 10-minute recovery periods
   ```

3. **Add exponential backoff**:
   ```python
   # Instead of fixed 3s delay
   delay = short_delay * (2 ** (attempt - 1))  # 3s, 6s, 12s, 24s, 48s
   ```

4. **Implement jitter**:
   ```python
   import random
   delay = short_delay + random.uniform(0, 2)  # Add randomness
   ```

5. **Add circuit breaker**:
   ```python
   if consecutive_failures > threshold:
       return None  # Stop trying entirely
   ```

## Error Handling Considerations

### Exception Specificity
```python
try:
    response = make_api_call(payload)
except RateLimitError as e:
    # Immediately trigger long delay
    time.sleep(long_delay)
except TimeoutError as e:
    # Use short delay
    time.sleep(short_delay)
except AuthenticationError as e:
    # Don't retry, fail immediately
    return None
except Exception as e:
    # Generic handling
    time.sleep(short_delay)
```

### Idempotency
Ensure operations are idempotent or implement deduplication:
```python
request_id = generate_unique_id()
payload['idempotency_key'] = request_id
```

## Real-World Example from Predictor Class

```python
# From src/core/Predictor.py lines 121-148
max_5min_retries = 6
retry_cycle = 0

while retry_cycle < max_5min_retries:
    for attempt in range(1, 6):  # 5 attempts
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", 
                            headers=headers, 
                            json=payload, 
                            timeout=60)
            r.raise_for_status()
            data = r.json()
            result = data["choices"][0]["message"]["content"]
            return result
        except Exception as e:
            print(f"{datetime.now()} LiteLLM request failed "
                  f"(attempt {attempt}/5, cycle {retry_cycle + 1}/"
                  f"{max_5min_retries}): {e}")
            if attempt < 5:
                time.sleep(3)
            else:
                retry_cycle += 1
                if retry_cycle < max_5min_retries:
                    print(f"{datetime.now()} All 5 retry attempts failed. "
                          f"Sleeping for 5 minutes before trying again "
                          f"(cycle {retry_cycle}/{max_5min_retries})...")
                    time.sleep(300)
                    break
                else:
                    print(f"{datetime.now()} Maximum retry cycles "
                          f"({max_5min_retries}) reached. Giving up.")
                    return None

return None
```

## Testing Strategy

### Unit Tests
```python
def test_retry_success_first_attempt():
    # Should return immediately without retries
    pass

def test_retry_success_after_failures():
    # Should succeed on attempt 3
    pass

def test_retry_exhaustion():
    # Should return None after all attempts
    pass

def test_retry_timing():
    # Verify delays are applied correctly
    pass
```

### Integration Tests
```python
def test_with_rate_limited_api():
    # Verify behavior with actual rate limits
    pass

def test_with_timeout_errors():
    # Verify timeout handling
    pass
```

## Performance Metrics to Track

1. **Success rate by attempt number**: Which attempt typically succeeds?
2. **Cycle utilization**: How often do we need outer cycles?
3. **Total retry time**: Average time spent in retry logic
4. **Failure patterns**: What exceptions occur most frequently?

## Summary

This retry pattern provides:
- **Resilience**: Handles both transient and persistent failures
- **Efficiency**: Quick recovery for temporary issues
- **Patience**: Extended recovery for rate limits/outages
- **Visibility**: Comprehensive logging for debugging
- **Flexibility**: Easy to customize for different scenarios

The two-tier approach balances responsiveness (quick inner retries) with robustness (patient outer cycles), making it ideal for batch processing operations that interact with external services.
