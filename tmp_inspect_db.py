import psycopg2
from app.config import Config

def inspect_database_logic():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        print("--- TRIGGERS ---")
        cur.execute("""
            SELECT tgname, tgenabled, pg_get_triggerdef(pg_trigger.oid)
            FROM pg_trigger
            JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid
            WHERE pg_class.relname = 'battery_telemetry';
        """)
        triggers = cur.fetchall()
        for t in triggers:
            print(f"Trigger: {t[0]}, Enabled: {t[1]}\nDef: {t[2]}\n")

        print("--- FOREIGN KEYS ON battery_telemetry ---")
        cur.execute("""
            SELECT conname, confdeltype, n.nspname AS schema_name, relname AS table_name
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            JOIN pg_class r ON r.oid = c.confrelid
            WHERE r.relname = 'battery_telemetry';
        """)
        constraints = cur.fetchall()
        for c in constraints:
            print(f"Constraint: {c[0]}, Type: {c[1]} (c=cascade, n=set null, r=restrict, a=no action), Table: {c[3]}")
            
        print("\n--- DELETION LOGS (Last 10) ---")
        try:
            cur.execute("SELECT * FROM battery_telemetry_deleted_log ORDER BY deleted_at DESC LIMIT 10;")
            logs = cur.fetchall()
            for l in logs:
                print(l)
        except Exception as e:
            print(f"Could not read deletion logs: {e}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_database_logic()
