from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'")
print(f"SITES_BAT_BAJA: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'")
print(f"TOTAL_BAT_BAJA_ALARMS: {cur.fetchone()[0]}")
conn.close()
