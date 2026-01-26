# Testing Instructions for Database API

This directory contains tests for the Database API client implementations.

## Test Files

1. **`test_api_database_client.py`** - Unit tests with mocks (no DB required)
2. **`test_database_client_methods.py`** - Verifies all methods exist and are callable
3. **`test_database_client_comparison.py`** - Integration tests comparing Local vs API results

## Python Tests (Local)

### Running Tests

```bash
# Run all API client unit tests (mocked)
pytest tests/adapters/test_api_database_client.py -v

# Verify all methods exist on both clients
pytest tests/adapters/test_database_client_methods.py -v

# Compare Local vs API results (requires both DB and API)
pytest tests/adapters/test_database_client_comparison.py -v

# Run all adapter tests
pytest tests/adapters/ -v
```

### Test Coverage

**Unit Tests (`test_api_database_client.py`):**
- ApiDatabaseClient initialization and configuration
- All database query methods (players, replays, build orders)
- Error handling (timeouts, unauthorized, etc.)
- Legacy compatibility properties
- Uses mocks - no database required

**Method Verification (`test_database_client_methods.py`):**
- Verifies all required methods exist on both LocalDatabaseClient and ApiDatabaseClient
- Checks method signatures match
- Tests return types
- Requires database/API to be available (skips if not)

**Integration Tests (`test_database_client_comparison.py`):**
- Compares results from LocalDatabaseClient vs ApiDatabaseClient
- Ensures both implementations produce identical results
- Tests all player operations, replay operations, and write operations
- Requires both local database AND API server to be available
- **Important:** Update test player names in the file to match your actual database

### Requirements

```bash
pip install pytest requests
```

## PHP Tests (Server-Side)

See `api-server/tests/README.md` for instructions on running the PHPUnit tests on the server.

## Integration Testing

To test the full stack and ensure API matches local:

1. **Start the PHP API server** (see `api-server/README.md`)
2. **Configure your local bot** to use API mode:
   ```python
   # settings/config.py
   DB_MODE = "api"
   DB_API_URL = "http://your-server.com/api-server/public"
   DB_API_KEY = "your-secret-api-key"
   ```
3. **Update test data** in `test_database_client_comparison.py`:
   - Change test player names to actual players in your database
   - Adjust test races to match your data
4. **Run comparison tests**:
   ```bash
   pytest tests/adapters/test_database_client_comparison.py -v
   ```
5. **Run the bot** and verify it connects to the remote API

### Test Data Setup

Before running comparison tests, edit `test_database_client_comparison.py` and update:
- `test_player = "kj"` → Use actual player names from your database
- `test_race = "Protoss"` → Use actual races
- `player1 = "kj"` and `player2 = "vales"` → Use actual player pairs

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

