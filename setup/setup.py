import mysql.connector
# from ..settings import config
# # Database connection parameters (modify these according to your database)
# db_params = {
#     'user': config.DB_USER,
#     'password': config.DB_PASSWORD,  # Replace with your MySQL password
#     'host': config.DB_HOST,
#     'database': config.DB_NAME,  # Replace with your database name
# }

db_params = {
    'user': 'root',
    'password': '',  # Replace with your MySQL password
    'host': 'localhost',
    'database': 'mathison',  # Replace with your database name
}

# SQL file to execute
sql_file = 'init_schema_down.sql'

# Establish a database connection
connection = mysql.connector.connect(**db_params)

# Create a cursor to execute SQL statements
cursor = connection.cursor()

# Read the SQL script from the file
with open(sql_file, 'r') as sql_script:
    sql_statements = sql_script.read()

# Split SQL statements by the delimiter (usually ';')
statements = sql_statements.split(';')

# Execute each SQL statement and commit
try:
    for statement in statements:
        cursor.execute(statement)
        connection.commit()
        print(statement)
        print("********sql statement***********")
    print("SQL script executed successfully.")
except mysql.connector.Error as err:
    print(f"Error: {err}")

# Close the cursor and connection
cursor.close()
connection.close()
