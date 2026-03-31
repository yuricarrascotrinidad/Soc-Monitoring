import sqlite3

# Conectar a la base de datos (crea archivo si no existe)
conn = sqlite3.connect('monitoring.db')
cursor = conn.cursor()

# 1️⃣ Listar todas las tablas de la base de datos
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = cursor.fetchall()

print("Tablas en la base de datos:")
for tabla in tablas:
    print("-", tabla[0])
conn.close()
