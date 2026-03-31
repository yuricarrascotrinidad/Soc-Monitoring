import psycopg2
from app.utils.db import get_db_connection

def check_counts():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Count distinct sites with active AC_FAIL
        cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL'")
        ac_fail_sites = cur.fetchone()[0]
        
        # Count total active AC_FAIL alarms
        cur.execute("SELECT COUNT(*) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL'")
        ac_fail_total = cur.fetchone()[0]
        
        # Count distinct sites with active BATERIA BAJA
        cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'")
        bat_baja_sites = cur.fetchone()[0]
        
        # Count total active BATERIA BAJA alarms
        cur.execute("SELECT COUNT(*) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'")
        bat_baja_total = cur.fetchone()[0]

        print(f"--- DATABASE STATUS ---")
        print(f"Sites with AC_FAIL (on): {ac_fail_sites}")
        print(f"Total AC_FAIL alarms (on): {ac_fail_total}")
        print(f"Sites with BATERIA BAJA (on): {bat_baja_sites}")
        print(f"Total BATERIA BAJA alarms (on): {bat_baja_total}")
        print(f"-----------------------")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_counts()
