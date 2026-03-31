import psycopg2
from app.config import Config

def check_overlap():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        sites = ['T2230_AN_PAUCAS', 'T3353_LL_ARCAYPATA']
        
        print("--- Site Details ---")
        for s in sites:
            cur.execute("SELECT sitio, precinct_id, vendor FROM battery_devices WHERE sitio = %s", (s,))
            row = cur.fetchone()
            print(f"Site: {s} -> {row}")

        device_id = '00001006000000002637'
        print(f"\n--- Device {device_id} ---")
        cur.execute("SELECT sitio, precinct_id FROM battery_devices WHERE device_id = %s", (device_id,))
        print("In battery_devices:", cur.fetchone())
        cur.execute("SELECT sitio FROM battery_telemetry WHERE device_id = %s", (device_id,))
        print("In battery_telemetry:", cur.fetchone())

        # Check all sites in the precinct of the device
        cur.execute("SELECT precinct_id FROM battery_devices WHERE device_id = %s", (device_id,))
        prec = cur.fetchone()
        if prec and prec[0]:
            p_id = prec[0]
            print(f"\n--- All sites for Precinct {p_id} ---")
            cur.execute("SELECT DISTINCT sitio FROM battery_devices WHERE precinct_id = %s", (p_id,))
            print([r[0] for r in cur.fetchall()])

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_overlap()
