# Testing Instructions for Database API

This directory contains tests for the Database API client implementations.

## Python Tests (Local)

These tests validate the `ApiDatabaseClient` that connects to the PHP API.

### Running Tests

```bash
# Run all API client tests
python tests/adapters/test_api_database_client.py

# Or use pytest
pytest tests/adapters/test_api_database_client.py -v
```

### Test Coverage

The Python tests cover:
- ApiDatabaseClient initialization and configuration
- All database query methods (players, replays, build orders)
- Error handling (timeouts, unauthorized, etc.)
- Legacy compatibility properties

### Requirements

```bash
pip install pytest requests
```

## PHP Tests (Server-Side)

See `api-server/tests/README.md` for instructions on running the PHPUnit tests on the server.

## Integration Testing

To test the full stack:

1. **Start the PHP API server** (see `api-server/README.md`)
2. **Configure your local bot** to use API mode:
   ```python
   # settings/config.py
   DB_MODE = "api"
   DB_API_URL = "http://your-server.com/api-server/public"
   DB_API_KEY = "your-secret-api-key"
   ```
3. **Run the bot** and verify it connects to the remote API

## Switching Between Modes

### Local Mode (Direct MySQL)
```python
DB_MODE = "local"
```

### API Mode (Remote MySQL via API)
```python
DB_MODE = "api"
DB_API_URL = "http://your-server.com/api-server/public"
DB_API_KEY = "your-secret-api-key"
```

The system will fail loudly if the chosen mode encounters any issues.

