import psycopg2
from app.config import Config

def read_deletion_logs():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        # Determine the table name (I saw 'battery_telemetry_deleted_l' truncated)
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'battery_telemetry_deleted%';")
        res = cur.fetchone()
        if not res:
            print("No deletion log table found starting with 'battery_telemetry_deleted'")
            return
        
        table_name = res[0]
        print(f"Reading logs from: {table_name}")
        
        cur.execute(f"SELECT id, deleted_at, device_id FROM {table_name} ORDER BY deleted_at DESC LIMIT 10;")
        rows = cur.fetchall()
        print(f"Total rows in log: {cur.rowcount}")
        for r in rows:
            print(f"ID: {r[0]} | Time: {r[1]} | Device: {r[2]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    read_deletion_logs()
