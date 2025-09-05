import mysql.connector
import sys
import os

# Add the parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from settings import config
    
    # Database connection parameters from config
    db_params = {
        'user': config.DB_USER,
        'password': config.DB_PASSWORD,
        'host': config.DB_HOST,
        'database': config.DB_NAME,
    }
    
    print(f"Connecting to database '{config.DB_NAME}' at {config.DB_HOST} as {config.DB_USER}")
    
except ImportError:
    print("WARNING: Could not import config. Using fallback parameters.")
    print("Make sure to update settings/config.py with your database credentials.")
    
    # Fallback database parameters (modify these according to your database)
    db_params = {
        'user': 'root',
        'password': '',  # Replace with your MySQL password
        'host': 'localhost',
        'database': 'mathison',  # Replace with your database name
    }

# SQL file to execute
sql_file = 'init_schema_up.sql'

print(f"Reading SQL schema from: {sql_file}")

try:
    # Establish a database connection
    connection = mysql.connector.connect(**db_params)
    print("Database connection established successfully.")

    # Create a cursor to execute SQL statements
    cursor = connection.cursor()

    # Read the SQL script from the file
    with open(sql_file, 'r', encoding='utf-8') as sql_script:
        sql_statements = sql_script.read()

    # Split SQL statements by the delimiter (usually ';')
    statements = [stmt.strip() for stmt in sql_statements.split(';') if stmt.strip()]

    print(f"Found {len(statements)} SQL statements to execute.")

    # Execute each SQL statement
    for i, statement in enumerate(statements, 1):
        try:
            print(f"Executing statement {i}/{len(statements)}...")
            cursor.execute(statement)
            connection.commit()
            print(f"✓ Statement {i} completed successfully")
        except mysql.connector.Error as stmt_err:
            print(f"✗ Error in statement {i}: {stmt_err}")
            print(f"Statement: {statement[:100]}...")
            connection.rollback()
            
    print("\n=== Database setup completed ===")
    print("You can now run the application.")
    
except mysql.connector.Error as err:
    print(f"Database error: {err}")
    sys.exit(1)
except FileNotFoundError:
    print(f"Error: SQL file '{sql_file}' not found.")
    print("Make sure you're running this script from the setup/ directory.")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    # Close the cursor and connection
    if 'cursor' in locals():
        cursor.close()
    if 'connection' in locals() and connection.is_connected():
        connection.close()
        print("Database connection closed.")
