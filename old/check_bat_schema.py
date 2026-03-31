import sqlite3
conn = sqlite3.connect('monitoring.db')
print(conn.execute("SELECT sql FROM sqlite_master WHERE name='battery_telemetry'").fetchone()[0])
conn.close()
