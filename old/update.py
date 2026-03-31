import sqlite3

conexion = sqlite3.connect("monitoring.db")
cursor = conexion.cursor()

sql = """
UPDATE alarmas
SET categoria = ?
WHERE categoria = ? AND alarma = ?
"""

valores = ("BATERIA BAJA", "No clasificado", "SOC")

cursor.execute(sql, valores)

conexion.commit()

print(f"Filas actualizadas: {cursor.rowcount}")

conexion.close()
