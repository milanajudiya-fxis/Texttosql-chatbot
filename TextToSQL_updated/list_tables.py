import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database credentials
# Note: If running locally while DB is in Docker, you might need to change DB_PORT to 3307
# or whatever port is mapped in docker-compose.yml
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "root")
db_name = os.getenv("DB_NAME", "TextToSQL")

print(f"Attempting to connect to database: {db_name} at {db_host}:{db_port} as {db_user}")

try:
    # Connect to the database
    connection = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

    print("Successfully connected!")

    with connection.cursor() as cursor:
        # Execute query to list tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print(f"\nTables in '{db_name}':")
        if not tables:
            print("No tables found.")
        else:
            for table in tables:
                # The key is usually 'Tables_in_<dbname>'
                print(f"- {list(table.values())[0]}")

except pymysql.MySQLError as e:
    print(f"Error connecting to database: {e}")
    print("\nTip: If you are running this locally and the DB is in Docker, check if you need to use port 3307.")

finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("\nConnection closed.")
