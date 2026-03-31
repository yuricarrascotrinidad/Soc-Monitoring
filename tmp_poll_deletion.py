import psycopg2
import time
from datetime import datetime
from app.config import Config

def monitor_site(site_name):
    print(f"Monitoring site: {site_name}")
    last_count = -1
    while True:
        try:
            conn = psycopg2.connect(
                host=Config.PG_HOST,
                port=Config.PG_PORT,
                database=Config.PG_DATABASE,
                user=Config.PG_USER,
                password=Config.PG_PASSWORD
            )
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM battery_telemetry WHERE sitio = %s", (site_name,))
            count = cur.fetchone()[0]
            
            if count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Total records for {site_name}: {count}")
                if count < last_count and last_count != -1:
                    print("!!! DELETION DETECTED !!!")
                    cur.execute("SELECT * FROM battery_telemetry WHERE sitio = %s", (site_name,))
                    records = cur.fetchall()
                    print(f"Remaining records: {records}")
                last_count = count
            
            # Check if any other records exist in the table generally
            cur.execute("SELECT COUNT(*) FROM battery_telemetry")
            total_count = cur.fetchone()[0]
            if total_count == 0 and last_count > 0:
                 print(f"[{datetime.now().strftime('%H:%M:%S')}] !!! ENTIRE TABLE CLEARED !!!")
            
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    monitor_site("T2230_AN_PAUCAS")
