import sqlite3
import os

DB_PATH = 'monitoring.db'

def check_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    tables = ['alarmas', 'battery_telemetry', 'notificaciones_enviadas']
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"Table {table}: {count} rows")
        except Exception as e:
            print(f"Error checking {table}: {e}")
            
    print("\nIndexes:")
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
    for row in cur.fetchall():
        print(f"Index: {row[0]}")
        print(f"SQL: {row[1]}")
        
    print("\nOldest and Newest Alarms:")
    try:
        cur.execute("SELECT MIN(hora), MAX(hora) FROM alarmas")
        oldest, newest = cur.fetchone()
        print(f"Oldest: {oldest}")
        print(f"Newest: {newest}")
    except:
        pass

    conn.close()

if __name__ == "__main__":
    check_stats()
