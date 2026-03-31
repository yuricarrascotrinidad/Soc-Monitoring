import psycopg2
import logging
from app.config import Config

def check_triggers():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        print("--- Checking Triggers ---")
        cur.execute("""
            SELECT trigger_name, event_manipulation, event_object_table, action_statement, action_orientation, action_timing
            FROM information_schema.triggers;
        """)
        triggers = cur.fetchall()
        for t in triggers:
            print(f"Trigger: {t[0]}, Event: {t[1]}, Table: {t[2]}, Timing: {t[5]}")
            print(f"Statement: {t[3]}\n")

        print("--- Checking All Functions (Procedures) ---")
        cur.execute("""
            SELECT proname, prosrc 
            FROM pg_proc 
            JOIN pg_namespace n ON n.oid = pg_proc.pronamespace
            WHERE n.nspname = 'public';
        """)
        funcs = cur.fetchall()
        for f in funcs:
            print(f"Function: {f[0]}")
            if 'delete' in f[0].lower() or 'battery' in f[0].lower():
                print(f"Source:\n{f[1]}\n")
            
        print("\n--- Checking Foreign Keys with CASCADE DELETE ---")
        cur.execute("""
            SELECT
                conname AS constraint_name,
                conrelid::regclass AS table_name,
                confrelid::regclass AS referenced_table,
                confdeltype AS delete_type
            FROM pg_constraint
            WHERE contype = 'f' AND confdeltype = 'c';
        """)
        fks = cur.fetchall()
        for fk in fks:
            print(f"Constraint: {fk[0]}, Table: {fk[1]}, Ref: {fk[2]}, Type: {fk[3]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_triggers()
