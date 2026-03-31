from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()

# Count by tipo (access/transport)
cur.execute("SELECT tipo, COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL' GROUP BY tipo")
print("AC_FAIL by TYPE:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Count by region
cur.execute("SELECT region, COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL' GROUP BY region")
print("AC_FAIL by REGION:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
