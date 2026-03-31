import psycopg2
from app.config import Config

def inspect_data():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    sitio = 'T2262_AN_COCHAPETI'
    print(f"--- Inspeccionando sitio: {sitio} ---")
    
    print("\n[alarmas_activas]")
    cur.execute("SELECT device_id, deviceName, alarma, categoria, hora FROM alarmas_activas WHERE sitio = %s AND categoria = 'BATERIA BAJA';", (sitio,))
    for row in cur.fetchall():
        print(row)

    print("\n[battery_telemetry]")
    cur.execute("SELECT device_id, nombre, soc, ultimo_update FROM battery_telemetry WHERE sitio = %s;", (sitio,))
    for row in cur.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    inspect_data()
