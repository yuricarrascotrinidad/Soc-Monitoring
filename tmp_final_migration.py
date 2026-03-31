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
        print("Set device_id to NOT NULL (cleaning NULLs first if any)...")
        cur.execute("DELETE FROM battery_telemetry WHERE device_id IS NULL OR device_id = '';")
        cur.execute("ALTER TABLE battery_telemetry ALTER COLUMN device_id SET NOT NULL;")

        print("Set nombre to NOT NULL (cleaning NULLs first if any)...")
        cur.execute("UPDATE battery_telemetry SET nombre = 'Unknown' WHERE nombre IS NULL OR nombre = '';")
        cur.execute("ALTER TABLE battery_telemetry ALTER COLUMN nombre SET NOT NULL;")

        print("Purging ALL duplicates for (device_id, nombre)...")
        cur.execute("""
            DELETE FROM battery_telemetry a
            USING battery_telemetry b
            WHERE a.id < b.id AND a.device_id = b.device_id AND a.nombre = b.nombre;
        """)
        print(f"Purged {cur.rowcount} duplicates.")

        print("Adding composite UNIQUE constraint...")
        cur.execute("ALTER TABLE battery_telemetry ADD CONSTRAINT battery_telemetry_did_name_unique UNIQUE (device_id, nombre);")
        
        conn.commit()
        print("Migration COMMITTED.")

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
