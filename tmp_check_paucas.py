import psycopg2
from app.config import Config

def check_site():
    output = []
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        site = 'T2230_AN_PAUCAS'
        
        output.append(f"--- Checking Telemetry for {site} ---")
        cur.execute("SELECT sitio, nombre, soc, voltaje, svoltage, current1, current2, ultimo_update, device_id FROM battery_telemetry WHERE sitio = %s;", (site,))
        telemetry = cur.fetchall()
        if not telemetry:
            output.append("No telemetry found.")
        else:
            for t in telemetry:
                output.append(str(t))
                
        output.append(f"\n--- Checking Devices for {site} ---")
        cur.execute("SELECT sitio, ip_gateway, vendor, precinct_id FROM battery_devices WHERE sitio = %s;", (site,))
        devices = cur.fetchall()
        if not devices:
            output.append("No devices found.")
        else:
            for d in devices:
                output.append(str(d))
                
        # Search for the specific device ID provided by the user
        device_id = '00001006000000002637'
        output.append(f"\n--- Searching for Device ID {device_id} ---")
        cur.execute("SELECT device_id, sitio, nombre, soc, voltaje, svoltage, ultimo_update FROM battery_telemetry WHERE device_id = %s OR device_id LIKE %s;", (device_id, f"{device_id}%"))
        telemetry_by_id = cur.fetchall()
        if not telemetry_by_id:
            output.append("No telemetry found for this device ID.")
        else:
            for tid in telemetry_by_id:
                output.append(str(tid))

        cur.execute("SELECT sitio, ip_gateway, vendor, precinct_id FROM battery_devices WHERE device_id = %s;", (device_id,))
        device_info = cur.fetchall()
        if not device_info:
            output.append("No device record found in battery_devices.")
        else:
            for di in device_info:
                output.append(str(di))

        conn.close()
    except Exception as e:
        output.append(f"Error: {e}")

    with open("db_check_result.txt", "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    check_site()
