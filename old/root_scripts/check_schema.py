import psycopg2
import os
import sys

# Add the project root to sys.path to import app.config
sys.path.append('c:\\Users\\ycarrasco\\Documents\\Project\\battery')
from app.config import Config

def check_columns():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'battery_telemetry'")
        columns = [row[0] for row in cur.fetchall()]
        print(f"COLUMNS: {columns}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_columns()
