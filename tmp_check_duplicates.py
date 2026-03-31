from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM alarmas_activas WHERE categoria='AC_FAIL'")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT sitio, alarma, hora FROM alarmas_activas WHERE categoria='AC_FAIL') as sub")
distinct = cur.fetchone()[0]
print(f"TOTAL_AC_FAIL: {total}, DISTINCT_AC_FAIL: {distinct}")
conn.close()
