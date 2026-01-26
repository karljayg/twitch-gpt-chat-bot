"""Test Fix 2: Time format normalization"""

# Test the time conversion logic directly
def normalize_time(raw_time):
    if isinstance(raw_time, str) and ':' in raw_time:
        try:
            parts = raw_time.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0
    else:
        return raw_time if isinstance(raw_time, (int, float)) else 0

print("=== Fix 2 Test: Time Format Normalization ===")

# Test cases
tests = [
    ("1:37", 97),    # String format
    ("2:00", 120),   # String format
    ("0:01", 1),     # String format
    (97, 97),        # Int format (already seconds)
    (120, 120),      # Int format
]

all_pass = True
for raw, expected in tests:
    result = normalize_time(raw)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_pass = False
    print(f"  {status} normalize_time({repr(raw)}) = {result} (expected {expected})")

if all_pass:
    print("\n✓ PASS: All time conversions correct!")
else:
    print("\n✗ FAIL: Some time conversions wrong")



