import psycopg2
from app.config import Config

def get_db_logic():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        print("--- TRIGGER DATA ---")
        cur.execute("""
            SELECT tgname, pg_get_triggerdef(tg.oid)
            FROM pg_trigger tg
            JOIN pg_class c ON tg.tgrelid = c.oid
            WHERE c.relname = 'battery_telemetry';
        """)
        for name, definition in cur.fetchall():
            print(f"Trigger: {name}\nDefinition: {definition}\n")

        print("--- FUNCTION DATA ---")
        cur.execute("""
            SELECT proname, pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE proname = 'log_battery_telemetry_delete';
        """)
        for name, definition in cur.fetchall():
            print(f"Function: {name}\nDefinition:\n{definition}\n")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_db_logic()
