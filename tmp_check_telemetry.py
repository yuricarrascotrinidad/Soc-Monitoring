import psycopg2
from app.config import Config

def check_battery_telemetry():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    # Check for the device_ids found in AC_FAIL alarms
    device_ids = ('0000100600002475', '0000100600002637')
    cur.execute("SELECT device_id, sitio, current1, current2, ultimo_update FROM battery_telemetry WHERE device_id IN %s", (device_ids,))
    rows = cur.fetchall()
    if not rows:
        print("No telemetry found for these devices.")
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    check_battery_telemetry()
