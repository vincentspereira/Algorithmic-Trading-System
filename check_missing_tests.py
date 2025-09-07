import os
import glob

def check_missing_tests():
    print("Checking for missing component test files...")
    
    # Component test files referenced in the execution framework
    component_tests = [
        'nautilus_trader_engine/risk/test_*.py',
        'nautilus_trader_engine/*/test_*.py',
        'database/tests/test_postgres.py',
        'database/tests/test_clickhouse.py',
        'database/tests/test_redis.py',
        'api/tests/test_health.py',
        'test_graphql_api.py',
        'api/tests/test_market_data.py',
        'api/trading.proto',
        'security/test_zero_trust_security.py'
    ]
    
    missing = []
    
    for test_pattern in component_tests:
        if '*' in test_pattern:
            # Handle glob patterns
            matches = glob.glob(test_pattern)
            if not matches:
                missing.append(test_pattern)
                print(f"Missing (no matches): {test_pattern}")
            else:
                print(f"Found {len(matches)} files matching: {test_pattern}")
        else:
            # Handle specific files
            if not os.path.exists(test_pattern):
                missing.append(test_pattern)
                print(f"Missing file: {test_pattern}")
            else:
                print(f"Found file: {test_pattern}")
    
    print(f"\nTotal missing component test files: {len(missing)}")
    if missing:
        print("Missing files:")
        for f in missing:
            print(f"  - {f}")
    
    return missing

if __name__ == "__main__":
    check_missing_tests()