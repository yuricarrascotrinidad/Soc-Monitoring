import psycopg2
from app.config import Config

def diagnose():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        device_id = '00001006000000002637'
        
        print(f"--- Diagnosing Device ID: {device_id} ---")
        
        cur.execute("SELECT device_id, sitio, nombre, soc, voltaje, svoltage, current1, ultimo_update FROM battery_telemetry WHERE device_id = %s;", (device_id,))
        telemetry = cur.fetchone()
        if telemetry:
            print("Telemetry in database:")
            cols = ['device_id', 'sitio', 'nombre', 'soc', 'voltaje', 'svoltage', 'current1', 'ultimo_update']
            for col, val in zip(cols, telemetry):
                print(f"  {col}: {val!r}")
        else:
            print("No telemetry found in database for this device ID.")

        cur.execute("SELECT device_id, sitio, ip_gateway, vendor, precinct_id FROM battery_devices WHERE device_id = %s;", (device_id,))
        device = cur.fetchone()
        if device:
            print("\nDevice info in battery_devices:")
            cols = ['device_id', 'sitio', 'ip_gateway', 'vendor', 'precinct_id']
            for col, val in zip(cols, device):
                print(f"  {col}: {val!r}")
        else:
            print("\nNo record in battery_devices for this device ID.")

        # Check if site 'T2230_AN_PAUCAS' has any other batteries
        print(f"\n--- Checking all batteries for site T2230_AN_PAUCAS ---")
        cur.execute("SELECT device_id, nombre, soc FROM battery_telemetry WHERE sitio = 'T2230_AN_PAUCAS';")
        site_bats = cur.fetchall()
        for bat in site_bats:
            print(f"  {bat}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose()
