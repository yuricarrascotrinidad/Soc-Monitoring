import psycopg2
from app.config import Config

def migrate_users_table():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        print("Adding first_name and last_name columns to users table...")
        cur.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
            ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Database migration completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate_users_table()
