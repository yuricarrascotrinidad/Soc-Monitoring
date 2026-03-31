import sqlite3
import os
import json
import logging

DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')

def migrate():
    print(f"Starting migration V3 (fixed) on {DB_PATH}...")
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # 1. Check if columns exist
        cursor = conn.execute("PRAGMA table_info(alarmas)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        # 2. Add columns if missing
        new_cols = [('deviceName', 'TEXT'), ('precinct_id', 'TEXT'), ('mete_name', 'TEXT')]
        for col_name, col_type in new_cols:
            if col_name not in columns:
                print(f"Adding column {col_name}...")
                conn.execute(f"ALTER TABLE alarmas ADD COLUMN {col_name} {col_type}")

        # 3. Migrate data
        print("Migrating data from alarmameta...")
        # Select all where deviceName is NULL but alarmameta might have content
        # Note: Using rowid as row_id to avoid Row key issues in some environments
        cursor = conn.execute("SELECT rowid as row_id, alarmameta FROM alarmas WHERE deviceName IS NULL")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} potential rows to fix.")
        count = 0
        for row in rows:
            rid = row['row_id']
            meta_raw = row['alarmameta']
            
            if not meta_raw:
                continue
                
            try:
                data = json.loads(meta_raw)
                dname = data.get('device_name', '')
                pid = data.get('precinct_id', '')
                mname = data.get('mete_name', '')
                
                conn.execute("""
                    UPDATE alarmas 
                    SET deviceName = ?, precinct_id = ?, mete_name = ?
                    WHERE rowid = ?
                """, (dname, pid, mname, rid))
                count += 1
            except:
                # If not JSON, maybe it's just a string name
                conn.execute("UPDATE alarmas SET deviceName = ? WHERE rowid = ?", (meta_raw, rid))
                count += 1
        
        conn.commit()
        print(f"Migration completed. Updated {count} rows.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
