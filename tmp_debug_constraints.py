import psycopg2
from app.config import Config

def debug_constraints():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    print("--- Detailed Constraints ---")
    cur.execute("""
        SELECT
            tc.constraint_name, 
            kcu.column_name, 
            tc.constraint_type
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
        WHERE tc.table_name = 'battery_telemetry'
        ORDER BY tc.constraint_name, kcu.ordinal_position;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n--- Checking for potential issues ---")
    # Check if 'nombre' is nullable
    cur.execute("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'battery_telemetry' AND column_name = 'nombre';")
    nullable = cur.fetchone()
    print(f"Is 'nombre' nullable? {nullable[0] if nullable else 'Unknown'}")

    conn.close()

if __name__ == "__main__":
    debug_constraints()
