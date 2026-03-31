import sqlite3
import json
from datetime import datetime

def verify_ac_voltage():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("Verifying AC Voltage implementation...")
    
    # 1. Check if column exists
    cur.execute("PRAGMA table_info(alarmas)")
    cols = [r['name'] for r in cur.fetchall()]
    if 'valor' in cols:
        print(" - Column 'valor' exists in 'alarmas' table.")
    else:
        print(" - ERROR: Column 'valor' NOT found in 'alarmas' table.")
        return

    # 2. Simulate saving an alarm with voltage
    print(" - Simulating saving an AC alarm with voltage...")
    test_alarm = {
        'tipo': 'access',
        'region': 'Ancash',
        'hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sitio': 'TEST_SITE_AC',
        'alarma': 'Test AC Failure',
        'categoria': 'AC_FAIL',
        'estado': 'on',
        'valor': 214.5,
        'deviceName': 'AC Monitor'
    }
    
    cur.execute("""
        INSERT INTO alarmas (tipo, region, hora, sitio, alarma, categoria, estado, valor, deviceName)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_alarm['tipo'], test_alarm['region'], test_alarm['hora'], test_alarm['sitio'], 
          test_alarm['alarma'], test_alarm['categoria'], test_alarm['estado'], test_alarm['valor'], test_alarm['deviceName']))
    conn.commit()
    
    # 3. Test API logic (SQL part)
    print(" - Testing query logic for get_ac_data...")
    cur.execute("""
        SELECT MAX(a.hora), a.tipo, a.region, a.sitio, a.deviceName, 
               GROUP_CONCAT(CASE WHEN a.valor IS NOT NULL THEN a.alarma || ' (' || a.valor || 'V)' ELSE a.alarma END, ' | ') as alarmas
        FROM alarmas a
        WHERE a.estado = 'on' AND a.categoria = 'AC_FAIL' AND a.sitio = 'TEST_SITE_AC'
        GROUP BY a.sitio, a.tipo, a.region
    """)
    row = cur.fetchone()
    if row:
        print(f" - Resulting alarm text: {row['alarmas']}")
        if "(214.5V)" in row['alarmas']:
            print(" - SUCCESS: Voltage is correctly formatted in the query.")
        else:
            print(" - ERROR: Voltage formatting failed.")
    else:
        print(" - ERROR: No row found for test site.")
        
    # Cleanup
    cur.execute("DELETE FROM alarmas WHERE sitio = 'TEST_SITE_AC'")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    verify_ac_voltage()
