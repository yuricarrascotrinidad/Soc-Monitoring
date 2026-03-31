import psycopg2
from app.config import Config

def fix_duplicates():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    # 1. Identify duplicates based on (device_id, nombre, sitio)
    cur.execute("""
        SELECT device_id, nombre, sitio, COUNT(*)
        FROM battery_telemetry
        GROUP BY device_id, nombre, sitio
        HAVING COUNT(*) > 1
    """)
    dups = cur.fetchall()
    print(f"Found {len(dups)} groups of duplicates.")
    
    if dups:
        # Keep only the newest record for each group
        # (Assuming 'ultimo_update' exists and is a timestamp)
        print("Cleaning up duplicates...")
        cur.execute("""
            DELETE FROM battery_telemetry a
            USING (
                SELECT MIN(ctid) as min_ctid, device_id, nombre, sitio
                FROM battery_telemetry
                GROUP BY device_id, nombre, sitio
            ) b
            WHERE a.device_id = b.device_id 
              AND a.nombre = b.nombre 
              AND a.sitio = b.sitio 
              AND a.ctid <> b.min_ctid
        """)
        print(f"Deleted {cur.rowcount} duplicate rows.")
    
    # 2. Add the UNIQUE constraint
    print("Adding UNIQUE constraint...")
    try:
        # Drop existing primary key if it exists but is named device_id
        # (Though we found there was no PK according to my previous check)
        cur.execute("ALTER TABLE battery_telemetry DROP CONSTRAINT IF EXISTS battery_telemetry_pkey")
        
        # Add the new unique constraint
        cur.execute("ALTER TABLE battery_telemetry ADD CONSTRAINT battery_telemetry_unique_key UNIQUE (device_id, nombre, sitio)")
        print("UNIQUE constraint added successfully.")
    except Exception as e:
        print(f"Error adding constraint: {e}")
        conn.rollback()
        return

    conn.commit()
    conn.close()

if __name__ == '__main__':
    fix_duplicates()
