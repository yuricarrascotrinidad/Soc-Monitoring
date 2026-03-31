import psycopg2
from app.config import Config

def check_schema():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'battery_telemetry' ORDER BY ordinal_position")
    cols = cur.fetchall()
    for col in cols:
        print(f"Column: {col[0]}, Type: {col[1]}")
    conn.close()

if __name__ == '__main__':
    check_schema()
