# Database Setup Scripts

This folder contains scripts to set up a fresh installation of the Mathison database.

## Files

- **`setup.py`** - Main setup script that creates all database tables
- **`init_schema_up.sql`** - SQL commands to create all tables and schema
- **`init_schema_down.sql`** - SQL commands to drop all tables (for cleanup)
- **`setup.sql`** - Complete setup script with database creation and all tables

## Prerequisites

1. MySQL server running
2. Python with `mysql-connector-python` installed
3. Database credentials configured in `../settings/config.py`

## Quick Start

### Option 1: Using Python Setup Script (Recommended)

```bash
cd setup/
python setup.py
```

The script will:
- Read database credentials from `../settings/config.py`
- Connect to your MySQL server
- Execute all SQL statements from `init_schema_up.sql`
- Create all necessary tables for the application

### Option 2: Manual SQL Execution

If you prefer to run SQL manually:

```bash
mysql -u yourusername -p < setup.sql
```

This will create the database and all tables in one go.

## Database Schema

The setup creates the following tables:

### Core Application Tables
- **`Players`** - SC2 player information (Id, SC2_UserId)
- **`Replays`** - Game replay data with all match details
- **`USER`** - User profile information
- **`MEMORY`** - AI conversation memory storage

### AI Personality Tables
- **`MAJOR_TRAITS`** - Personality trait definitions
- **`MOOD_TYPE`** - Available mood types
- **`MOODS`** - Mood probability settings
- **`MOTIVATIONS`** - Motivation definitions
- **`CORE_VALUES`** - Core value definitions
- **`GOALS`** - Goal definitions
- **`PERSONALITY`** - Links personality components together

## Configuration

Make sure your `../settings/config.py` has the correct database settings:

```python
DB_HOST = "localhost"
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_NAME = "mathison"
```

## Cleanup

To remove all tables and start fresh:

```bash
cd setup/
python -c "
import mysql.connector
from settings import config
conn = mysql.connector.connect(host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME)
cursor = conn.cursor()
with open('init_schema_down.sql', 'r') as f:
    for stmt in f.read().split(';'):
        if stmt.strip():
            cursor.execute(stmt)
conn.commit()
conn.close()
print('All tables dropped successfully.')
"
```

## Troubleshooting

### Connection Issues
- Verify MySQL server is running
- Check database credentials in config.py
- Ensure the specified database exists

### Permission Issues
- Make sure your MySQL user has CREATE, DROP, and INSERT privileges
- For new installations, you may need to create the database first:
  ```sql
  CREATE DATABASE mathison;
  ```

### Foreign Key Errors
- If you get foreign key constraint errors, run the cleanup script first
- Make sure you're running the full setup, not partial table creation

## Schema Validation

After setup, you can verify the installation by checking table counts:

```python
from models.mathison_db import Database
db = Database()
cursor = db.cursor
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
print(f"Created {len(tables)} tables successfully")
cursor.close()
db.connection.close()
``` 