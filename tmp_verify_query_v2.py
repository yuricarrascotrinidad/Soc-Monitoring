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
        SELECT DISTINCT sitio, region, device_id, devicename as nombre, tipo as tipo_sistema, categoria
        FROM alarmas_activas
        WHERE estado = 'on'
        AND (
            categoria IN ('Bateria Lit. disc.', 'BATERIA BAJA', 'AC_FAIL')
            OR (devicename LIKE '%%ZTE%%' OR alarma LIKE '%%ZTE%%')
        )
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    print(f"Total rows found: {len(rows)}")
    ac_fail_rows = [row for row in rows if row[5] == 'AC_FAIL']
    print(f"AC_FAIL rows found: {len(ac_fail_rows)}")
    
    for row in ac_fail_rows:
        print(f"AC_FAIL Device: {row[2]} Site: {row[0]}")
            
    conn.close()

if __name__ == "__main__":
    verify_query()
