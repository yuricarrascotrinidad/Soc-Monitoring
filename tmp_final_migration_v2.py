import psycopg2
from app.config import Config

def finalize_migration():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    try:
        print("Cleaning and hardening battery_telemetry...")
        
        # 1. Clean NULLs / Empties
        cur.execute("DELETE FROM battery_telemetry WHERE device_id IS NULL OR device_id = '' OR nombre IS NULL OR nombre = '';")
        
        # 2. Set NOT NULL
        cur.execute("ALTER TABLE battery_telemetry ALTER COLUMN device_id SET NOT NULL;")
        cur.execute("ALTER TABLE battery_telemetry ALTER COLUMN nombre SET NOT NULL;")

        # 3. Purge duplicates using ctid
        cur.execute("""
            DELETE FROM battery_telemetry a
            WHERE a.ctid <> (
                SELECT min(b.ctid)
                FROM battery_telemetry b
                WHERE a.device_id = b.device_id AND a.nombre = b.nombre
            );
        """)
        print(f"Purged {cur.rowcount} duplicates.")

        # 4. Add composite UNIQUE constraint
        # Drop if exists first (though it shouldn't be there)
        cur.execute("ALTER TABLE battery_telemetry DROP CONSTRAINT IF EXISTS battery_telemetry_did_name_unique;")
        cur.execute("ALTER TABLE battery_telemetry ADD CONSTRAINT battery_telemetry_did_name_unique UNIQUE (device_id, nombre);")
        
        conn.commit()
        print("Migration COMMITTED successfully.")

        # FINAL VERIFICATION
        cur.execute("""
            SELECT tc.constraint_name 
            FROM information_schema.table_constraints tc 
            WHERE tc.table_name = 'battery_telemetry' AND tc.constraint_type = 'UNIQUE';
        """)
        constraints = cur.fetchall()
        print(f"Verified constraints: {constraints}")
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    finalize_migration()
