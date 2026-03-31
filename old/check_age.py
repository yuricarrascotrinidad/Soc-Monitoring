import sqlite3
from datetime import datetime, timedelta

db_path = 'monitoring.db'
conn = sqlite3.connect(db_path)
try:
    print("--- Row Counts by Age ---")
    ahora = datetime.now()
    
    # Check rows older than 24h
    limite_24h = (ahora - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute("SELECT COUNT(*) FROM alarmas WHERE hora < ?", (limite_24h,))
    older_than_24h = cur.fetchone()[0]
    
    # Check rows older than 24h that are 'on'
    cur = conn.execute("SELECT COUNT(*) FROM alarmas WHERE hora < ? AND estado = 'on'", (limite_24h,))
    on_older_than_24h = cur.fetchone()[0]
    
    # Check rows older than 7 days
    limite_7d = (ahora - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute("SELECT COUNT(*) FROM alarmas WHERE hora < ?", (limite_7d,))
    older_than_7d = cur.fetchone()[0]
    
    print(f"Total rows older than 24h: {older_than_24h}")
    print(f"Total 'on' rows older than 24h: {on_older_than_24h}")
    print(f"Total rows older than 7 days: {older_than_7d}")
    
    print("\n--- Top Categories for older records ---")
    cur = conn.execute("SELECT categoria, COUNT(*) as count FROM alarmas WHERE hora < ? GROUP BY categoria ORDER BY count DESC LIMIT 5", (limite_24h,))
    for row in cur.fetchall():
        print(f"{row[0]}: {row[1]}")

finally:
    conn.close()
