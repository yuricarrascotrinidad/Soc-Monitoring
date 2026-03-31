import psycopg2
from app.config import Config

def dump_telemetry():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT device_id, sitio, nombre, ultimo_update FROM battery_telemetry;")
        rows = cur.fetchall()
        print(f"Total records in battery_telemetry: {len(rows)}")
        for r in rows:
            print(r)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_telemetry()
