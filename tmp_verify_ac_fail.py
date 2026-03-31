from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE categoria='AC_FAIL'")
print(f"VERIFIED_AC_FAIL_SITES: {cur.fetchone()[0]}")
conn.close()
