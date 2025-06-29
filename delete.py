import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def drop_all_tables():
    DATABASE_URL = os.getenv('DATABASE_URL')

    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file.")
        return

    result = urlparse(DATABASE_URL)

    dbname = result.path[1:]
    user = result.username
    password = result.password
    host = result.hostname
    port = result.port or 5432

    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("Dropping all tables in schema 'public'...")
        cursor.execute("DROP SCHEMA public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        print("✅ All tables dropped and schema reset.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error connecting or dropping tables: {e}")

if __name__ == '__main__':
    drop_all_tables()