# API Server Comparison: Mathison vs PsiStorm

This document compares the two API servers available in this repository.

## Quick Comparison

| Feature | **Mathison API** | **PsiStorm API** |
|---------|-----------------|-----------------|
| **Database** | `mathison` | `psistorm` |
| **Type** | Fixed Business Logic | Generic CRUD |
| **Port** | 8000 | 8001 |
| **Tables** | Replays, Players, Comments, Patterns | Any table in database |
| **Endpoints** | 16 specific endpoints | 9 generic endpoints |
| **Discovery** | ❌ No | ✅ Yes (list tables, schemas) |
| **Raw SQL** | ❌ No | ✅ Yes (SELECT only) |
| **Use Case** | SC2 bot integration | Database admin, analytics |

---

## Mathison API

**Purpose**: StarCraft II replay analysis and player tracking  
**Directory**: `api-server/`  
**Documentation**: `documentation/API_SPECIFICATION.md`

### Key Features
- SC2-specific business logic
- Player and race existence checks
- Replay information retrieval
- Player comments and patterns
- Build order extraction
- Head-to-head matchup stats

### Example Endpoints
```bash
GET  /api/v1/players/check?player_name=X&player_race=Y
GET  /api/v1/players/{name}/records
GET  /api/v1/replays/latest
POST /api/v1/comments/save
POST /api/v1/patterns/save
```

### Best For
- ✅ SC2 Twitch bot integration
- ✅ Replay analysis automation
- ✅ Player tracking
- ✅ Pattern learning systems
- ✅ Specific business logic

### Not Suitable For
- ❌ General database queries
- ❌ Ad-hoc reporting
- ❌ Database administration
- ❌ Dynamic table access

---

## PsiStorm API

**Purpose**: Generic database access for any table  
**Directory**: `api-psistorm/`  
**Documentation**: `documentation/API_PSISTORM_SPECIFICATION.md`

### Key Features
- Query any table dynamically
- Full CRUD operations (SELECT, INSERT, UPDATE, DELETE)
- Table discovery (list tables, get schemas)
- Raw SQL queries (SELECT only)
- Flexible filtering, sorting, pagination
- Optional read-only mode

### Example Endpoints
```bash
GET    /api/v1/tables                           # List all tables
GET    /api/v1/tables/{name}/schema             # Get table structure
POST   /api/v1/tables/{name}/select             # Query any table
POST   /api/v1/tables/{name}/insert             # Insert data
PUT    /api/v1/tables/{name}/update             # Update data
DELETE /api/v1/tables/{name}/delete             # Delete data
POST   /api/v1/query/raw                        # Custom SQL
```

### Best For
- ✅ Database administration tools
- ✅ Analytics dashboards
- ✅ Data migration
- ✅ Custom reports
- ✅ Third-party integrations
- ✅ Exploratory analysis

### Not Suitable For
- ❌ When you need complex business logic
- ❌ When you want to hide database structure
- ❌ When table names should be abstracted

---

## When to Use Each API

### Use Mathison API When:
1. **Bot integration**: Your SC2 Twitch bot needs replay data
2. **Specific workflows**: You need the exact endpoints for player tracking
3. **Business logic**: Endpoints should enforce specific rules
4. **Abstraction**: You want to hide database structure from clients
5. **Stability**: Endpoints won't change, providing a stable contract

**Example**: "My Twitch bot needs to check if I've played against 'Atlantis' as Protoss and get player comments."

### Use PsiStorm API When:
1. **Flexibility**: You don't know which tables you'll need
2. **Exploration**: You want to explore the database dynamically
3. **Admin tools**: Building a database management interface
4. **Analytics**: Creating dashboards with custom queries
5. **Migration**: Exporting/importing data
6. **Rapid development**: Don't want to create endpoints for each query

**Example**: "I need to build a dashboard showing stats from multiple tables, and I want to write custom SQL queries."

---

## Running Both APIs Simultaneously

You can run both APIs on the same server without conflict:

```bash
# Terminal 1: Mathison API
cd api-server
php -S localhost:8000 -t public

# Terminal 2: PsiStorm API  
cd api-psistorm
php -S localhost:8001 -t public
```

### Production URLs
```
Mathison API:  https://psistorm.com/api-server/public
PsiStorm API:  https://psistorm.com/api-psistorm/public
```

---

## Security Comparison

### Mathison API Security
- ✅ Bearer token authentication
- ✅ Fixed endpoints (limited attack surface)
- ✅ Business logic validation
- ✅ Specific table access only
- ❌ No read-only mode
- ❌ No table exclusion

### PsiStorm API Security
- ✅ Bearer token authentication
- ✅ SQL injection protection (parameterized queries)
- ✅ Read-only mode option
- ✅ Table exclusion list
- ✅ Row limit configuration
- ✅ UPDATE/DELETE require WHERE clause
- ⚠️ Broader attack surface (any table access)
- ⚠️ Raw SQL allowed (SELECT only)

**Recommendation**: Use PsiStorm API in read-only mode for analytics/reporting if you don't need write access.

---

## Code Examples

### Mathison API: Check Player
```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/players/check",
    headers={"Authorization": "Bearer YOUR_KEY"},
    params={"player_name": "Atlantis", "player_race": "Protoss"}
)
player_data = response.json()
```

### PsiStorm API: Query Any Table
```python
import requests

# Discover tables first
tables = requests.get(
    "http://localhost:8001/api/v1/tables",
    headers={"Authorization": "Bearer YOUR_KEY"}
).json()['tables']

# Query any table
response = requests.post(
    "http://localhost:8001/api/v1/tables/users/select",
    headers={"Authorization": "Bearer YOUR_KEY"},
    json={"where": {"status": "active"}, "limit": 10}
)
users = response.json()['rows']
```

---

## Migration Path

### From Mathison API to PsiStorm API

If you have code using Mathison API and want to use PsiStorm API:

**Before (Mathison)**:
```python
response = requests.get(
    "http://localhost:8000/api/v1/players/check",
    params={"player_name": "Atlantis", "player_race": "Protoss"}
)
```

**After (PsiStorm)**:
```python
response = requests.post(
    "http://localhost:8001/api/v1/tables/Replays/select",
    json={
        "where": {
            "Player1_Name": "Atlantis",
            "Player1_Race": "Protoss"
        },
        "limit": 1,
        "order_by": {"column": "Date_Played", "direction": "DESC"}
    }
)
```

**Note**: You'll need to know the database schema to query directly.

---

## Performance Comparison

### Mathison API
- **Optimized queries**: Specific SQL for each endpoint
- **Less overhead**: Direct business logic execution
- **Better for**: High-frequency bot operations

### PsiStorm API
- **Generic queries**: Built dynamically from parameters
- **More overhead**: JSON parsing, query building
- **Better for**: Ad-hoc queries, exploration

**Recommendation**: Use Mathison API for production bot operations, PsiStorm API for analytics and reporting.

---

## Documentation

### Mathison API Documentation
- **Quick Start**: `documentation/API_QUICK_START.md`
- **Full Spec**: `documentation/API_SPECIFICATION.md` (1000+ lines)
- **README**: `api-server/README.md`

### PsiStorm API Documentation
- **README**: `api-psistorm/README.md`
- **Full Spec**: `documentation/API_PSISTORM_SPECIFICATION.md` (1200+ lines)
- **Summary**: `API_PSISTORM_COMPLETE.md`

---

## Recommendation Summary

| Scenario | Recommended API | Reason |
|----------|----------------|---------|
| SC2 Twitch bot | **Mathison** | Purpose-built for replay data |
| Database admin UI | **PsiStorm** | Dynamic table access |
| Analytics dashboard | **PsiStorm** | Flexible queries, raw SQL |
| Player tracking | **Mathison** | Specific endpoints |
| Data export/import | **PsiStorm** | Generic CRUD operations |
| Third-party integration | **PsiStorm** | Flexible, discoverable |
| Production bot queries | **Mathison** | Optimized, stable |
| Custom reports | **PsiStorm** | Raw SQL support |

---

## Summary

**Both APIs are production-ready and serve different purposes:**

- **Mathison API**: Specialized, optimized, business-logic-driven
- **PsiStorm API**: Generic, flexible, exploration-friendly

**You can use both simultaneously** depending on your use case. Consider using Mathison API for your bot and PsiStorm API for administrative and analytical tasks.
