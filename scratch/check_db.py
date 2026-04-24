import psycopg2
from psycopg2 import extras
import os

PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DATABASE = 'monitoring'
PG_USER = 'postgres'
PG_PASSWORD = 'yofc'

def check_db():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        print("Checking battery_telemetry for ZTE entries...")
        cur.execute("SELECT * FROM battery_telemetry WHERE nombre LIKE '%ZTE%' LIMIT 10")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        
        print("\nChecking battery_telemetry_global for ZTE entries...")
        cur.execute("SELECT * FROM battery_telemetry_global WHERE nombre LIKE '%ZTE%' LIMIT 10")
        rows = cur.fetchall()
        for row in rows:
            print(row)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
