from app.utils.db import get_db_connection
import psycopg2.extras

conn = get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Check columns in alarmas_activas
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='alarmas_activas' ORDER BY ordinal_position")
cols = [r['column_name'] for r in cur.fetchall()]
print("COLUMNS:", cols)

# Check a sample AC_FAIL row to see if precinct_id is stored
cur.execute("SELECT sitio, precinct_id, device_id, devicename, categoria, hora FROM alarmas_activas WHERE categoria='AC_FAIL' AND estado='on' LIMIT 5")
rows = cur.fetchall()
print("\nSAMPLE ROWS:")
for r in rows:
    print(f"  {r['sitio']} | precinct={r['precinct_id']} | device={r['device_id']} | name={r['devicename']} | hora={r['hora']}")

conn.close()
