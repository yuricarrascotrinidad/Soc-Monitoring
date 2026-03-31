import sqlite3
import os
import logging

DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')

def migrate():
    logging.basicConfig(level=logging.INFO)
    print(f"Starting migration on {DB_PATH}...")
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.execute("PRAGMA table_info(alarmas)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'device_id' not in columns:
            print("Adding 'device_id' column to 'alarmas' table...")
            conn.execute("ALTER TABLE alarmas ADD COLUMN device_id TEXT")
            conn.commit()
            print("Column 'device_id' added successfully.")
        else:
            print("Column 'device_id' already exists in 'alarmas' table. Skipping.")
            
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
