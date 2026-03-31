import psycopg2
from app.config import Config

def check_shared_ids():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    sitio = 'A4199_SM_NAVARRO'
    print(f"--- Investigando sitio: {sitio} ---")
    
    cur.execute("SELECT device_id FROM alarmas_activas WHERE sitio = %s AND categoria = 'BATERIA BAJA' LIMIT 1;", (sitio,))
    res = cur.fetchone()
    if not res:
        print("No se encontró alarma para este sitio.")
        return
    
    did = res[0]
    print(f"Device ID de la alarma: {did}")
    
    print("\n[battery_telemetry] Sitios que comparten este device_id:")
    cur.execute("SELECT sitio, nombre, soc, ultimo_update FROM battery_telemetry WHERE device_id = %s;", (did,))
    for row in cur.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    check_shared_ids()
