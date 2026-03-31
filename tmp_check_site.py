import psycopg2
from app.config import Config

def check_site_data(site_search):
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        print(f"--- Checking Alarms for '{site_search}' ---")
        cur.execute("SELECT * FROM alarmas_activas WHERE sitio LIKE %s;", (f"%{site_search}%",))
        alarms = cur.fetchall()
        for a in alarms:
            print(a)
            
        print(f"\n--- Checking Telemetry for '{site_search}' ---")
        cur.execute("SELECT sitio, nombre, soc, voltaje, svoltage, current1, current2, ultimo_update FROM battery_telemetry WHERE sitio LIKE %s;", (f"%{site_search}%",))
        telemetry = cur.fetchall()
        for t in telemetry:
            print(t)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_site_data("T2230")
