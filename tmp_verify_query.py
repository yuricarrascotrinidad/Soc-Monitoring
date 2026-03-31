import psycopg2
from app.config import Config

def verify_query():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    # This is the updated query from monitoring_service.py
    query = """
        SELECT DISTINCT sitio, region, device_id, devicename as nombre, tipo as tipo_sistema
        FROM alarmas_activas
        WHERE estado = 'on'
        AND (
            categoria IN ('Bateria Lit. disc.', 'BATERIA BAJA', 'AC_FAIL')
            OR (devicename LIKE '%%ZTE%%' OR alarma LIKE '%%ZTE%%')
        )
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    found_ac_fail = False
    for row in rows:
        # Check if any AC_FAIL device is now in the results
        # We'll check if our previously identified device_ids are there
        if row[2] in ('0000100600002475', '0000100600002637'):
            print(f"Verified: Device {row[2]} for site {row[0]} (AC_FAIL) is now included in telemetry collection.")
            found_ac_fail = True
    
    if not found_ac_fail:
        print("AC_FAIL devices not found in query results.")
        # Print first few rows to see what is there
        print("First 5 results:")
        for row in rows[:5]:
            print(row)
            
    conn.close()

if __name__ == "__main__":
    verify_query()
