from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT region, COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL' AND tipo = 'access' GROUP BY region")
print("ACCESS_AC_FAIL_BY_REGION:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn.close()
