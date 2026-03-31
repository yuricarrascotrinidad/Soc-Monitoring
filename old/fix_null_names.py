import sqlite3
import os

DB_PATH = 'monitoring.db'

def fix_null_names():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        
        # Count rows to be updated
        cur.execute("""
            SELECT count(*) 
            FROM alarmas a
            JOIN battery_telemetry t ON a.device_id = t.device_id
            WHERE (a.deviceName IS NULL OR a.deviceName = '') 
              AND t.nombre IS NOT NULL 
              AND t.nombre != ''
        """)
        to_fix = cur.fetchone()[0]
        print(f"Found {to_fix} rows to fix using telemetry data.")
        
        if to_fix > 0:
            cur.execute("""
                UPDATE alarmas
                SET deviceName = (
                    SELECT nombre 
                    FROM battery_telemetry 
                    WHERE battery_telemetry.device_id = alarmas.device_id
                )
                WHERE (deviceName IS NULL OR deviceName = '')
                  AND EXISTS (
                    SELECT 1 
                    FROM battery_telemetry 
                    WHERE battery_telemetry.device_id = alarmas.device_id 
                      AND nombre IS NOT NULL 
                      AND nombre != ''
                  )
            """)
            conn.commit()
            print(f"Updated {cur.rowcount} rows.")
        else:
            print("No rows found that could be fixed with current telemetry data.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_null_names()
