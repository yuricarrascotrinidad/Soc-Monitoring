import sqlite3

conn = sqlite3.connect("monitoring.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM alarmas where estado = 'off'")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()