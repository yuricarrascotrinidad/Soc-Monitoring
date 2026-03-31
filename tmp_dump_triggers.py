import psycopg2
from app.config import Config

def dump_triggers():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        # Get all triggers for battery_telemetry
        cur.execute("""
            SELECT 
                tgname, 
                pg_get_triggerdef(pg_trigger.oid)
            FROM pg_trigger
            JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid
            WHERE pg_class.relname = 'battery_telemetry';
        """)
        triggers = cur.fetchall()
        print(f"--- Triggers on battery_telemetry ---")
        for name, def_sql in triggers:
            print(f"Name: {name}")
            print(f"Def: {def_sql}\n")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_triggers()
