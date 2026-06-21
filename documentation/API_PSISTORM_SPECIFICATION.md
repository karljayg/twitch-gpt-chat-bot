# PsiStorm Database API Specification

**Version**: 1.0  
**Last Updated**: 2026-02-03  
**Type**: Generic Table Query API

## Overview

This REST API provides secure, flexible access to **any table** in the PsiStorm database. Unlike the Mathison API which has fixed endpoints for specific tables, this API allows dynamic querying of any table with full CRUD operations.

## Base URL

```
https://psistorm.com/api-psistorm/public
```

**Local Development**:
```
http://localhost:8001
```

## Authentication

All API requests (except `/health`) require Bearer token authentication.

### Headers Required

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

## Key Features

- 🔍 **Dynamic Table Access** - Query any table without predefined endpoints
- 🔒 **Secure** - Parameterized queries prevent SQL injection
- 📊 **Discovery** - List tables, inspect schemas, get row counts
- ✏️ **Full CRUD** - SELECT, INSERT, UPDATE, DELETE operations
- 🔐 **Flexible Security** - Read-only mode, table exclusions, row limits
- 💻 **Raw SQL** - Execute custom SELECT queries

## Response Format

All responses return JSON with appropriate HTTP status codes.

### Success Response
```json
{
  "data": { ... },
  "count": 10
}
```

### Error Response
```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden (read-only mode)
- `500` - Internal Server Error

---

## Discovery Endpoints

### 1. Health Check

Check API availability and database connection.

**Endpoint**: `GET /health`  
**Authentication**: Not required

#### Example Request
```bash
curl http://localhost:8001/health
```

#### Example Response
```json
{
  "status": "healthy",
  "timestamp": 1738598400,
  "database": "connected",
  "api_version": "v1",
  "api_type": "generic"
}
```

---

### 2. List All Tables

Get a list of all accessible tables in the database.

**Endpoint**: `GET /api/v1/tables`

#### Example Request
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables
```

#### Example Response
```json
{
  "tables": [
    "users",
    "posts",
    "comments",
    "categories",
    "tags"
  ],
  "count": 5
}
```

---

### 3. Get Table Schema

Retrieve the structure/schema of a specific table.

**Endpoint**: `GET /api/v1/tables/{table_name}/schema`

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `table_name` | string | Yes | Name of the table |

#### Example Request
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables/users/schema
```

#### Example Response
```json
{
  "table": "users",
  "columns": [
    {
      "Field": "id",
      "Type": "int(11)",
      "Null": "NO",
      "Key": "PRI",
      "Default": null,
      "Extra": "auto_increment"
    },
    {
      "Field": "username",
      "Type": "varchar(255)",
      "Null": "NO",
      "Key": "UNI",
      "Default": null,
      "Extra": ""
    },
    {
      "Field": "email",
      "Type": "varchar(255)",
      "Null": "NO",
      "Key": "",
      "Default": null,
      "Extra": ""
    },
    {
      "Field": "created_at",
      "Type": "timestamp",
      "Null": "NO",
      "Key": "",
      "Default": "CURRENT_TIMESTAMP",
      "Extra": ""
    }
  ]
}
```

---

### 4. Get Table Row Count

Get the total number of rows in a table.

**Endpoint**: `GET /api/v1/tables/{table_name}/count`

#### Example Request
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8001/api/v1/tables/users/count
```

#### Example Response
```json
{
  "table": "users",
  "count": 1523
}
```

---

## Query Endpoints

### 5. SELECT from Table

Query data from any table with flexible filtering, ordering, and pagination.

**Endpoint**: `POST /api/v1/tables/{table_name}/select`

#### Request Body
```json
{
  "columns": ["id", "username", "email"],
  "where": {
    "status": "active",
    "role": "admin"
  },
  "order_by": {
    "column": "created_at",
    "direction": "DESC"
  },
  "limit": 10,
  "offset": 0
}
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `columns` | array | No | Column names to select (default: all) |
| `where` | object | No | Key-value pairs for WHERE conditions (AND logic) |
| `order_by` | object | No | Sort configuration: `{column, direction}` |
| `limit` | integer | No | Max rows to return (capped by server config) |
| `offset` | integer | No | Skip N rows (for pagination) |

#### Example Request
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": ["id", "username", "email"],
    "where": {"status": "active"},
    "order_by": {"column": "created_at", "direction": "DESC"},
    "limit": 5
  }' \
  http://localhost:8001/api/v1/tables/users/select
```

#### Example Response
```json
{
  "table": "users",
  "rows": [
    {
      "id": 123,
      "username": "john_doe",
      "email": "john@example.com"
    },
    {
      "id": 122,
      "username": "jane_smith",
      "email": "jane@example.com"
    }
  ],
  "count": 2
}
```

#### Example: Get All Rows (No Filters)
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8001/api/v1/tables/users/select
```

---

### 6. INSERT into Table

Add a new row to a table.

**Endpoint**: `POST /api/v1/tables/{table_name}/insert`

#### Request Body
```json
{
  "data": {
    "username": "new_user",
    "email": "newuser@example.com",
    "status": "active",
    "role": "user"
  }
}
```

#### Example Request
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "username": "new_user",
      "email": "newuser@example.com",
      "status": "active"
    }
  }' \
  http://localhost:8001/api/v1/tables/users/insert
```

#### Example Response
```json
{
  "success": true,
  "insert_id": 124,
  "rows_affected": 1
}
```

**Note**: Disabled when `$read_only_mode = true` in config.

---

### 7. UPDATE Table

Update existing rows in a table.

**Endpoint**: `PUT /api/v1/tables/{table_name}/update`

#### Request Body
```json
{
  "data": {
    "status": "inactive",
    "updated_at": "2026-02-03 12:00:00"
  },
  "where": {
    "id": 123
  }
}
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | object | Yes | Key-value pairs to update |
| `where` | object | Yes | Conditions (prevents accidental full-table updates) |

#### Example Request
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

#### Example Response
```json
{
  "success": true,
  "rows_affected": 1
}
```

**Safety**: `where` parameter is **required** to prevent accidental full-table updates.

---

### 8. DELETE from Table

Delete rows from a table.

**Endpoint**: `DELETE /api/v1/tables/{table_name}/delete`

#### Request Body
```json
{
  "where": {
    "id": 123
  }
}
```

#### Example Request
```bash
curl -X DELETE \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "where": {"id": 123}
  }' \
  http://localhost:8001/api/v1/tables/users/delete
```

#### Example Response
```json
{
  "success": true,
  "rows_affected": 1
}
```

**Safety**: `where` parameter is **required** to prevent accidental full-table deletes.

---

### 9. Raw SQL Query

Execute custom SQL SELECT queries.

**Endpoint**: `POST /api/v1/query/raw`

#### Request Body
```json
{
  "sql": "SELECT u.username, COUNT(p.id) as post_count FROM users u LEFT JOIN posts p ON u.id = p.user_id WHERE u.status = ? GROUP BY u.id ORDER BY post_count DESC LIMIT ?",
  "params": ["active", 10]
}
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sql` | string | Yes | SELECT query (only SELECT allowed) |
| `params` | array | No | Parameterized values for `?` placeholders |

#### Example Request
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT username, email FROM users WHERE status = ? LIMIT ?",
    "params": ["active", 5]
  }' \
  http://localhost:8001/api/v1/query/raw
```

#### Example Response
```json
{
  "rows": [
    {"username": "john_doe", "email": "john@example.com"},
    {"username": "jane_smith", "email": "jane@example.com"}
  ],
  "count": 2
}
```

**Security**:
- Only `SELECT` queries are allowed
- Use parameterized queries with `params` array
- Do NOT concatenate user input into SQL string

---

## Security Configuration

The API supports several security features configured in `config.php`:

### Read-Only Mode
```php
$read_only_mode = true;  // Disables INSERT, UPDATE, DELETE
```

When enabled, write operations return `403 Forbidden`.

### Row Limit
```php
$max_rows_per_query = 1000;  // Maximum rows per SELECT
```

Prevents massive data dumps.

### Table Exclusion
```php
$excluded_tables = [
    'passwords',
    'api_keys',
    'sensitive_data'
];
```

Hidden tables won't appear in `/api/v1/tables` and can't be queried.

---

## Code Examples

### Python

```python
import requests

API_URL = "http://localhost:8001"
API_KEY = "your_api_key_here"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List all tables
def get_tables():
    response = requests.get(f"{API_URL}/api/v1/tables", headers=headers)
    return response.json()['tables']

# Get table schema
def get_schema(table_name):
    response = requests.get(
        f"{API_URL}/api/v1/tables/{table_name}/schema",
        headers=headers
    )
    return response.json()['columns']

# Query table
def query_table(table_name, where=None, limit=10):
    payload = {"limit": limit}
    if where:
        payload["where"] = where
    
    response = requests.post(
        f"{API_URL}/api/v1/tables/{table_name}/select",
        headers=headers,
        json=payload
    )
    return response.json()['rows']

# Insert data
def insert_data(table_name, data):
    response = requests.post(
        f"{API_URL}/api/v1/tables/{table_name}/insert",
        headers=headers,
        json={"data": data}
    )
    return response.json()

# Example usage
tables = get_tables()
print(f"Available tables: {tables}")

users = query_table("users", where={"status": "active"}, limit=5)
print(f"Found {len(users)} active users")

result = insert_data("users", {
    "username": "newuser",
    "email": "newuser@example.com",
    "status": "active"
})
print(f"Inserted user with ID: {result['insert_id']}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8001';
const API_KEY = 'your_api_key_here';

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// List all tables
async function getTables() {
  const response = await axios.get(`${API_URL}/api/v1/tables`, { headers });
  return response.data.tables;
}

// Query table
async function queryTable(tableName, where = null, limit = 10) {
  const payload = { limit };
  if (where) payload.where = where;
  
  const response = await axios.post(
    `${API_URL}/api/v1/tables/${tableName}/select`,
    payload,
    { headers }
  );
  return response.data.rows;
}

// Insert data
async function insertData(tableName, data) {
  const response = await axios.post(
    `${API_URL}/api/v1/tables/${tableName}/insert`,
    { data },
    { headers }
  );
  return response.data;
}

// Update data
async function updateData(tableName, data, where) {
  const response = await axios.put(
    `${API_URL}/api/v1/tables/${tableName}/update`,
    { data, where },
    { headers }
  );
  return response.data;
}

// Example usage
(async () => {
  const tables = await getTables();
  console.log('Tables:', tables);
  
  const users = await queryTable('users', { status: 'active' }, 5);
  console.log(`Found ${users.length} users`);
  
  const result = await insertData('users', {
    username: 'newuser',
    email: 'newuser@example.com'
  });
  console.log('Insert ID:', result.insert_id);
})();
```

### cURL Examples

```bash
#!/bin/bash

API_URL="http://localhost:8001"
API_KEY="your_api_key_here"

# List tables
curl -H "Authorization: Bearer ${API_KEY}" \
  "${API_URL}/api/v1/tables"

# Get table schema
curl -H "Authorization: Bearer ${API_KEY}" \
  "${API_URL}/api/v1/tables/users/schema"

# Query table
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"where": {"status": "active"}, "limit": 5}' \
  "${API_URL}/api/v1/tables/users/select"

# Insert data
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {"username": "newuser", "email": "user@example.com"}}' \
  "${API_URL}/api/v1/tables/users/insert"

# Update data
curl -X PUT \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"data": {"status": "inactive"}, "where": {"id": 123}}' \
  "${API_URL}/api/v1/tables/users/update"

# Delete data
curl -X DELETE \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"where": {"id": 123}}' \
  "${API_URL}/api/v1/tables/users/delete"

# Raw SQL query
curl -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users WHERE status = ? LIMIT ?", "params": ["active", 5]}' \
  "${API_URL}/api/v1/query/raw"
```

---

## Use Cases

### 1. Database Explorer/Admin Tool
Build a web-based database viewer:
```javascript
// Get all tables, then display each table's data
const tables = await getTables();
for (const table of tables) {
  const schema = await getSchema(table);
  const rows = await queryTable(table, null, 100);
  displayTable(table, schema, rows);
}
```

### 2. Analytics Dashboard
Query specific data for dashboards:
```python
# Get user growth over time
result = raw_query("""
    SELECT DATE(created_at) as date, COUNT(*) as new_users
    FROM users
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY DATE(created_at)
    ORDER BY date
""")
```

### 3. Data Migration
Export/import data between databases:
```python
# Export
tables = get_tables()
for table in tables:
    data = query_table(table, limit=10000)
    save_to_file(f"{table}.json", data)

# Import
for table in tables:
    data = load_from_file(f"{table}.json")
    for row in data:
        insert_data(table, row)
```

### 4. Reporting System
Generate custom reports:
```javascript
const reportData = await rawQuery({
  sql: `
    SELECT 
      u.username,
      COUNT(DISTINCT p.id) as posts,
      COUNT(DISTINCT c.id) as comments
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    LEFT JOIN comments c ON u.id = c.user_id
    WHERE u.created_at >= ?
    GROUP BY u.id
    ORDER BY posts DESC
    LIMIT 10
  `,
  params: ['2026-01-01']
});
```

---

## Error Handling

### Common Errors

#### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```
**Fix**: Check API key in Authorization header.

#### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "API is in read-only mode"
}
```
**Fix**: Set `$read_only_mode = false` in config, or use SELECT only.

#### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Missing required parameter: where (safety measure)"
}
```
**Fix**: Provide required parameters (e.g., `where` for UPDATE/DELETE).

#### 500 Database Error
```json
{
  "error": "Database Error",
  "message": "Access to table 'passwords' is restricted"
}
```
**Fix**: Table is in `$excluded_tables` list.

---

## Comparison: PsiStorm API vs Mathison API

| Feature | PsiStorm API | Mathison API |
|---------|--------------|--------------|
| **Database** | `psistorm` | `mathison` |
| **Port** | 8001 | 8000 |
| **Table Access** | Dynamic (any table) | Fixed (Replays, Players, etc.) |
| **Endpoints** | Generic CRUD | Business logic (SC2-specific) |
| **Discovery** | List tables, schemas | No discovery |
| **Raw SQL** | Yes (SELECT only) | No |
| **Use Case** | General database access | SC2 replay analysis |
| **Flexibility** | High | Low (intentionally) |

---

## Best Practices

### 1. Always Use Parameterized Queries
```javascript
// Good
rawQuery({
  sql: "SELECT * FROM users WHERE status = ?",
  params: ["active"]
});

// Bad (SQL injection risk)
rawQuery({
  sql: `SELECT * FROM users WHERE status = '${userInput}'`
});
```

### 2. Implement Pagination
```python
def get_all_users_paginated(page_size=100):
    offset = 0
    while True:
        users = query_table("users", limit=page_size, offset=offset)
        if not users:
            break
        yield users
        offset += page_size
```

### 3. Use Discovery Endpoints
```javascript
// Before querying, check if table exists and get schema
const tables = await getTables();
if (tables.includes('users')) {
  const schema = await getSchema('users');
  // Now safely query based on schema
}
```

### 4. Handle Errors Gracefully
```python
try:
    result = insert_data("users", data)
except requests.HTTPError as e:
    if e.response.status_code == 403:
        print("API is in read-only mode")
    else:
        print(f"Error: {e.response.json()['message']}")
```

---

## Support

For API access, bug reports, or questions:
- **Email**: admin@psistorm.com
- **Documentation**: This file
- **Setup Guide**: `api-psistorm/README.md`

---

## Changelog

### Version 1.0 (2026-02-03)
- Initial generic API release
- 9 endpoints documented
- Full CRUD operations
- Table discovery
- Raw SQL queries
- Security features (read-only mode, table exclusion, row limits)
