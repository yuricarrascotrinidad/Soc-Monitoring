from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    SELECT a.sitio, a.tipo, a.region, a.deviceName, a.device_id
    FROM alarmas_activas a
    WHERE a.estado = 'on' AND a.categoria = 'AC_FAIL'
    GROUP BY a.sitio, a.tipo, a.region, a.deviceName, a.device_id
""")
rows = cur.fetchall()
print(f"DASHBOARD_ROWS: {len(rows)}")
conn.close()
