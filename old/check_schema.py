import sqlite3

def check_schema():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    cur = conn.execute("PRAGMA table_info(alarmas)")
    columns = [row['name'] for row in cur.fetchall()]
    print(f"Columns in alarmas: {columns}")
    
    # Check if battery_telemetry exists
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='battery_telemetry'")
    if cur.fetchone():
        cur = conn.execute("PRAGMA table_info(battery_telemetry)")
        print(f"Columns in battery_telemetry: {[row['name'] for row in cur.fetchall()]}")
    
    conn.close()

if __name__ == "__main__":
    check_schema()
