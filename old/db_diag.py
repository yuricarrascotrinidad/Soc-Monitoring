import sqlite3
import os

db_path = 'monitoring.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
try:
    print("--- Database Stats ---")
    size = os.path.getsize(db_path) / (1024*1024)
    wal_size = os.path.getsize(db_path + '-wal') / (1024*1024) if os.path.exists(db_path + '-wal') else 0
    print(f"DB Size: {size:.2f} MB")
    print(f"WAL Size: {wal_size:.2f} MB")
    
    print("\n--- Schema for alarmas ---")
    cur = conn.execute("SELECT sql FROM sqlite_master WHERE name='alarmas'")
    print(cur.fetchone()[0])
    
    print("\n--- Indexes ---")
    cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='alarmas'")
    for row in cur.fetchall():
        print(f"Index: {row[0]}\nSQL: {row[1]}")
        
    print("\n--- Row counts ---")
    cur = conn.execute("SELECT COUNT(*) FROM alarmas")
    print(f"Total alarms: {cur.fetchone()[0]}")
    
    cur = conn.execute("SELECT COUNT(*) FROM battery_telemetry")
    print(f"Total battery telemetry: {cur.fetchone()[0]}")
    
    print("\n--- Pragma info ---")
    print(f"Journal Mode: {conn.execute('PRAGMA journal_mode').fetchone()[0]}")
    print(f"Synchronous: {conn.execute('PRAGMA synchronous').fetchone()[0]}")
    
finally:
    conn.close()
