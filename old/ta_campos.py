import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('monitoring.db')
cursor = conn.cursor()

# Obtener la estructura de la tabla 'alarmas'
cursor.execute("PRAGMA table_info(alarmas);")
columnas = cursor.fetchall()

print("Campos de la tabla 'alarmas':")
for col in columnas:
    # col[1] es el nombre de la columna
    print(f"- {col[1]} (tipo: {col[2]})")

# Cerrar conexión
conn.close()
