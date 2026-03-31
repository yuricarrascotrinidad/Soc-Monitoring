import sqlite3

conn = sqlite3.connect("monitoring.db")
cursor = conn.cursor()

tablas = [
    "alarmas",
    "access_cameras",
    "transport_cameras",
    "notificaciones_enviadas",
    "battery_telemetry"
]

for tabla in tablas:
    cursor.execute(f"DELETE FROM {tabla};")

# Reiniciar autoincrement
cursor.execute("DELETE FROM sqlite_sequence;")

conn.commit()
conn.close()

print("Todos los registros fueron eliminados correctamente.")