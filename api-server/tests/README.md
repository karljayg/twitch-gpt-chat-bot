# API Server Tests

This folder contains tests for the Mathison Database API.

## PHP Tests (Server-Side)

Test the API directly on the server without needing the Python client.

### Running Tests

```bash
# From api-server directory
php tests/api_test.php

# With custom URL and API key
php tests/api_test.php http://localhost:8000 your-api-key

# On production server
php tests/api_test.php https://yourdomain.com/mathison-api your-production-key
```

### What It Tests

- ✅ Health check endpoint
- ✅ Authentication (reject invalid keys, accept valid keys)
- ✅ All player endpoints
- ✅ All replay endpoints
- ✅ Build order extraction
- ✅ Error handling (400, 401, 404)
- ✅ Parameter validation

### Output

```
========================================
Mathison API Test Suite
========================================
Base URL: http://localhost:8000
API Key: test-api-k...
========================================

Test #1: Health check (no auth required)
✓ PASS

Test #2: Auth: Reject request without API key
✓ PASS

...

========================================
Test Results
========================================
Total:  15
Passed: 15
Failed: 0
========================================
All tests passed!
```

## Python Tests (Client-Side)

Test the Python client connecting to the API.

### Running Tests

```bash
# From project root
pytest tests/adapters/test_api_database_client.py -v

# With coverage
pytest tests/adapters/test_api_database_client.py -v --cov=adapters/database

# Run all tests including API tests
pytest tests/ -v
```

### What It Tests

- ✅ ApiDatabaseClient initialization
- ✅ Request authentication headers
- ✅ All database methods
- ✅ Error handling (timeouts, 401, exceptions)
- ✅ Factory pattern (local vs API mode)
- ✅ Legacy compatibility (cursor/connection properties)

### Requirements

Tests use mocking, so API doesn't need to be running for Python tests.

For integration testing with real API:
1. Start API server: `cd api-server && composer start`
2. Run integration tests: `pytest tests/integration/ -v` (when we create them)

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Test API Server (PHP)
  run: |
    cd api-server
    composer install
    php tests/api_test.php http://localhost:8000 test-key

- name: Test Python Client
  run: |
    pytest tests/adapters/test_api_database_client.py -v
```

