import psycopg2
from app.config import Config

def debug_schema():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    print("--- Table Definition ---")
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'battery_telemetry';
    """)
    for row in cur.fetchall():
        print(row)

    print("\n--- Constraints ---")
    cur.execute("""
        SELECT conname, pg_get_constraintdef(oid) 
        FROM pg_constraint 
        WHERE conrelid = 'battery_telemetry'::regclass;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n--- Unique Indexes ---")
    cur.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'battery_telemetry';
    """)
    for row in cur.fetchall():
        print(row)

    print("\n--- Any NULLs in device_id or nombre? ---")
    cur.execute("SELECT COUNT(*) FROM battery_telemetry WHERE device_id IS NULL;")
    print(f"NULL device_id: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM battery_telemetry WHERE nombre IS NULL;")
    print(f"NULL nombre: {cur.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    debug_schema()
