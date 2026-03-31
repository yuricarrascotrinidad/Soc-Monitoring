from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT alarma, COUNT(*) FROM alarmas_activas WHERE categoria='AC_FAIL' GROUP BY alarma")
res = cur.fetchall()
print('ALARM_NAME_COUNTS:')
for r in res:
    print(f"  {r[0]}: {r[1]}")
conn.close()
