import sqlite3
import os
import json

DB_PATH = 'monitoring.db'

def inspect():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check schema
    print("--- Table Info: alarmas ---")
    cursor = conn.execute("PRAGMA table_info(alarmas)")
    for col in cursor.fetchall():
        print(dict(col))
        
    # Check NULLs for BATERIA BAJA
    print("\n--- NULL deviceName count (BATERIA BAJA) ---")
    cursor = conn.execute("SELECT count(*) FROM alarmas WHERE deviceName IS NULL AND categoria = 'BATERIA BAJA'")
    print(f"NULL deviceName (BATERIA BAJA): {cursor.fetchone()[0]}")
    
    # Check some rows
    print("\n--- Sample BATERIA BAJA rows ---")
    cursor = conn.execute("""
        SELECT a.sitio, a.deviceName, t.nombre as telemetry_name, a.device_id
        FROM alarmas a
        LEFT JOIN battery_telemetry t ON a.device_id = t.device_id
        WHERE a.categoria = 'BATERIA BAJA' 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(dict(row))

    conn.close()

if __name__ == "__main__":
    inspect()
