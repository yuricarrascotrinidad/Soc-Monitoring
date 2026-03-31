import sqlite3
import json

def check_a4012():
    conn = sqlite3.connect('monitoring.db')
    cur = conn.cursor()
    
    print("--- Alarms for A4012_SM_VALLE DE LA CONQUISTA ---")
    cur.execute("SELECT * FROM alarmas WHERE sitio = 'A4012_SM_VALLE DE LA CONQUISTA'")
    for r in cur.fetchall():
        print(r)
        
    print("\n--- Battery Telemetry for A4012_SM_VALLE DE LA CONQUISTA ---")
    cur.execute("SELECT * FROM battery_telemetry WHERE sitio = 'A4012_SM_VALLE DE LA CONQUISTA'")
    for r in cur.fetchall():
        print(r)
        
    conn.close()

if __name__ == "__main__":
    check_a4012()
