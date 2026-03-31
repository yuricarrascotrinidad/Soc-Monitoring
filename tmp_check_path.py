import psycopg2
from app.config import Config

def check_schema_details():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    print("--- Search Path ---")
    cur.execute("SHOW search_path;")
    print(cur.fetchone())

    print("\n--- Table Schema ---")
    cur.execute("""
        SELECT table_schema 
        FROM information_schema.tables 
        WHERE table_name = 'battery_telemetry';
    """)
    print(cur.fetchall())

    conn.close()

if __name__ == "__main__":
    check_schema_details()
