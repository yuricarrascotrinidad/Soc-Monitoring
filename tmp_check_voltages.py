from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT valor, COUNT(*) FROM alarmas_activas WHERE categoria='AC_FAIL' GROUP BY valor ORDER BY valor ASC")
res = cur.fetchall()
print('VOLTAGE_COUNTS:')
for r in res:
    print(f"  {r[0]}: {r[1]}")
conn.close()
