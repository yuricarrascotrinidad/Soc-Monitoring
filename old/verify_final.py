import sqlite3

def verify():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    
    print("Checking active highlights logic...")
    # These should NOT trigger highlights (has_battery_alarm: false)
    query_soc = "SELECT count(*) FROM alarmas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'"
    print(f"Active SOC (BATERIA BAJA) alarms: {conn.execute(query_soc).fetchone()[0]}")
    
    # These SHOULD trigger highlights (has_battery_alarm: true)
    query_hw = "SELECT count(*) FROM alarmas WHERE estado = 'on' AND categoria = 'Bateria'"
    print(f"Active Hardware (Bateria) alarms: {conn.execute(query_hw).fetchone()[0]}")
    
    # Sample check for hardware alarms
    cur = conn.execute("SELECT alarma, categoria, device_id FROM alarmas WHERE estado = 'on' AND categoria = 'Bateria' LIMIT 5")
    rows = cur.fetchall()
    if rows:
        print("\nSample Hardware Alarms:")
        for r in rows:
            print(f" - {r['alarma']} (Category: {r['categoria']})")
            
    conn.close()

if __name__ == "__main__":
    verify()
