
import sqlite3
conn = sqlite3.connect('monitoring.db')
cursor = conn.cursor()
cursor.execute("SELECT nombre, voltaje, carga, ultimo_update FROM battery_telemetry WHERE sitio = 'T1045_AR_TARUCANI'")
rows = cursor.fetchall()
for r in rows:
    print(r)
conn.close()
