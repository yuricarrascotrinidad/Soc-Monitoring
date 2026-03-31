import sqlite3
import os

DB_PATH = 'monitoring.db'

def inspect_battery_telemetry():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("--- Table Info: battery_telemetry ---")
    cursor = conn.execute("PRAGMA table_info(battery_telemetry)")
    for col in cursor.fetchall():
        print(dict(col))
        
    print("\n--- Index Info: battery_telemetry ---")
    cursor = conn.execute("PRAGMA index_list(battery_telemetry)")
    indexes = cursor.fetchall()
    for idx in indexes:
        print(dict(idx))
        idx_name = idx['name']
        cursor2 = conn.execute(f"PRAGMA index_info({idx_name})")
        for col in cursor2.fetchall():
            print(f"  Column: {dict(col)}")

    conn.close()

if __name__ == "__main__":
    inspect_battery_telemetry()
