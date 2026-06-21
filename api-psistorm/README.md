# PsiStorm Database API

Generic REST API for flexible querying of any table in the PsiStorm database.

## Features

- ✅ Query **any table** dynamically
- ✅ Full CRUD operations (SELECT, INSERT, UPDATE, DELETE)
- ✅ Raw SQL queries (SELECT only for security)
- ✅ Table introspection (list tables, get schema, row counts)
- ✅ Secure parameterized queries (SQL injection protection)
- ✅ Optional read-only mode
- ✅ Configurable row limits
- ✅ Table exclusion list for sensitive data
- ✅ Bearer token authentication

## Quick Start

### 1. Install Dependencies

```bash
composer install
```

### 2. Configure

```bash
cp config.example.php config.php
# Edit config.php with your credentials
```

**Important config options**:
```php
$db_config['database'] = 'psistorm';  // Your database name
$api_key = 'your-secure-api-key';     // Generate with: openssl rand -base64 32
$read_only_mode = false;              // Set to true for read-only access
$max_rows_per_query = 1000;           // Limit rows per query
$excluded_tables = [];                // Tables to hide from API
```

### 3. Deploy to Server

Copy the `api-psistorm` folder to your web server (same location as `api-server`).

**That's it!** Apache/Nginx automatically serves it at:
```
https://yourdomain.com/api-psistorm/public/health
```

## API Endpoints

### Discovery Endpoints

#### List All Tables
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables
```

Response:
```json
{
  "tables": ["users", "posts", "comments"],
  "count": 3
}
```

#### Get Table Schema
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables/users/schema
```

Response:
```json
{
  "table": "users",
  "columns": [
    {"Field": "id", "Type": "int(11)", "Null": "NO", "Key": "PRI"},
    {"Field": "username", "Type": "varchar(255)", "Null": "NO", "Key": ""}
  ]
}
```

#### Get Row Count
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables/users/count
```

### Query Endpoints

#### SELECT from Table
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": ["id", "username", "email"],
    "where": {"status": "active"},
    "order_by": {"column": "created_at", "direction": "DESC"},
    "limit": 10,
    "offset": 0
  }' \
  http://localhost:8001/api/v1/tables/users/select
```

**All fields are optional**:
- `columns`: Array of column names (default: all columns)
- `where`: Key-value pairs for WHERE conditions (AND logic)
- `order_by`: `{"column": "name", "direction": "ASC|DESC"}`
- `limit`: Max rows (capped by config)
- `offset`: Skip rows (for pagination)

#### INSERT into Table
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "username": "newuser",
      "email": "user@example.com",
      "status": "active"
    }
  }' \
  http://localhost:8001/api/v1/tables/users/insert
```

Response:
```json
{
  "success": true,
  "insert_id": 123,
  "rows_affected": 1
}
```

#### UPDATE Table
```bash
curl -X PUT \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"status": "inactive"},
    "where": {"id": 123}
  }' \
  http://localhost:8001/api/v1/tables/users/update
```

**Requires WHERE** for safety (prevents accidental full table updates).

#### DELETE from Table
```bash
curl -X DELETE \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"id": 123}
  }' \
  http://localhost:8001/api/v1/tables/users/delete
```

**Requires WHERE** for safety (prevents accidental full table deletes).

#### Raw SQL Query (SELECT only)
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT u.username, COUNT(p.id) as post_count FROM users u LEFT JOIN posts p ON u.id = p.user_id WHERE u.status = ? GROUP BY u.id",
    "params": ["active"]
  }' \
  http://localhost:8001/api/v1/query/raw
```

**Security**: Only SELECT queries are allowed. Use parameterized queries with `params` array.

## Security Features

### 1. API Key Authentication
All endpoints (except `/health`) require Bearer token:
```http
Authorization: Bearer YOUR_API_KEY
```

### 2. SQL Injection Protection
- All queries use prepared statements
- User input is parameterized
- No direct SQL execution from user input

### 3. Read-Only Mode
Set in config to disable INSERT/UPDATE/DELETE:
```php
$read_only_mode = true;
```

### 4. Row Limit
Prevents massive data dumps:
```php
$max_rows_per_query = 1000;
```

### 5. Table Exclusion
Hide sensitive tables from API access:
```php
$excluded_tables = ['passwords', 'api_keys'];
```

## Example: Python Client

```python
import requests

API_URL = "http://localhost:8001"
API_KEY = "your_api_key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List tables
response = requests.get(f"{API_URL}/api/v1/tables", headers=headers)
tables = response.json()['tables']
print("Tables:", tables)

# Query a table
response = requests.post(
    f"{API_URL}/api/v1/tables/users/select",
    headers=headers,
    json={
        "where": {"status": "active"},
        "limit": 10
    }
)
users = response.json()['rows']
print(f"Found {len(users)} users")

# Insert data
response = requests.post(
    f"{API_URL}/api/v1/tables/users/insert",
    headers=headers,
    json={
        "data": {
            "username": "newuser",
            "email": "user@example.com"
        }
    }
)
print("Insert ID:", response.json()['insert_id'])
```

## Deployment

### Production Setup

1. **Copy to server**:
```bash
scp -r api-psistorm user@server:/var/www/html/
```

2. **Install dependencies**:
```bash
cd /var/www/html/api-psistorm
composer install --no-dev --optimize-autoloader
```

3. **Configure**:
```bash
cp config.example.php config.php
nano config.php  # Set production credentials
chmod 644 config.php
```

4. **Set base path** if under subdirectory:
```php
$base_path = '/api-psistorm/public';
```

5. **Enable mod_rewrite** (Apache):
```bash
sudo a2enmod rewrite
sudo systemctl restart apache2
```

## Documentation

For complete API documentation with more examples:
- **[Generic API Specification](../documentation/API_PSISTORM_SPECIFICATION.md)**

## Differences from Mathison API

| Feature | Mathison API | PsiStorm API |
|---------|--------------|--------------|
| **Tables** | Fixed (Replays, Players, etc.) | Dynamic (any table) |
| **Endpoints** | Specific business logic | Generic CRUD operations |
| **Database** | `mathison` | `psistorm` |
| **Port** | 8000 | 8001 |
| **Use Case** | SC2 replay data | General purpose queries |

## Troubleshooting

### 401 Unauthorized
- Check API key in config.php matches request
- Verify Authorization header format: `Bearer YOUR_KEY`

### 403 Forbidden (INSERT/UPDATE/DELETE)
- Check if `$read_only_mode = true` in config

### 500 Database Error
- Verify database credentials in config.php
- Check database exists: `SHOW DATABASES;`
- Test connection: `mysql -u user -p psistorm`

### Empty tables list
- Check `$excluded_tables` in config
- Verify database has tables: `SHOW TABLES;`

## Next Steps

1. Run `composer install` to install dependencies
2. Copy `config.example.php` to `config.php` and configure
3. Generate secure API key: `openssl rand -base64 32`
4. Copy folder to production server (next to `api-server`)
5. Share API documentation with developers
