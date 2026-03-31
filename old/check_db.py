import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'monitoring.db')
print(f"Checking DB at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:", tables)
    
    # Check columns for a table if it exists
    for table_name in [t[0] for t in tables]:
        print(f"\nSchema for {table_name}:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
