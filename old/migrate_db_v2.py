import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')

def migrate():
    print(f"Starting migration V2 on {DB_PATH}...")
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        
        # Create battery_telemetry table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS battery_telemetry (
                device_id TEXT PRIMARY KEY,
                soc REAL,
                carga REAL,
                descarga REAL,
                ultimo_update DATETIME
            )
        """)
        
        conn.commit()
        print("Table 'battery_telemetry' created or already exists.")
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
