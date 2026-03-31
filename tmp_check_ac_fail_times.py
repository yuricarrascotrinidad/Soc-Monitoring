from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT MIN(hora), MAX(hora), COUNT(*) FROM alarmas_activas WHERE categoria='AC_FAIL'")
res = cur.fetchone()
print(f"AC_FAIL_MIN_HORA: {res[0]}")
print(f"AC_FAIL_MAX_HORA: {res[1]}")
print(f"AC_FAIL_COUNT: {res[2]}")
conn.close()
