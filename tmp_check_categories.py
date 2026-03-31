from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT categoria, COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' GROUP BY categoria")
print("CATEGORIA_COUNTS:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn.close()
