import psycopg2
from app.config import Config

def check_ac_fail_alarms():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT sitio, region, device_id, devicename, tipo FROM alarmas_activas WHERE categoria = 'AC_FAIL' AND estado = 'on' LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    check_ac_fail_alarms()
