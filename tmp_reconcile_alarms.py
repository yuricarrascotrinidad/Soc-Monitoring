from app.utils.db import get_db_connection
import psycopg2.extras

conn = get_db_connection()
cur = conn.cursor()

print("Reconciling AC_FAIL alarms...")

try:
    # 1. Move everything older than 2 hours to history
    cur.execute("""
        INSERT INTO alarmas_historicas (tipo, region, hora, duracion, sitio, alarma, deviceName, precinct_id, mete_name, categoria, estado, device_id, valor)
        SELECT tipo, region, hora, duracion, sitio, alarma, deviceName, precinct_id, mete_name, categoria, 'off', device_id, valor
        FROM alarmas_activas
        WHERE hora < NOW() - INTERVAL '2 hours'
        RETURNING id
    """)
    moved_count = len(cur.fetchall())
    
    # 2. Delete from active
    cur.execute("DELETE FROM alarmas_activas WHERE hora < NOW() - INTERVAL '2 hours'")
    
    conn.commit()
    print(f"Moved {moved_count} stale alarms to history.")
    
    # 3. Current count
    cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE categoria='AC_FAIL'")
    print(f"Current AC_FAIL sites: {cur.fetchone()[0]}")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
