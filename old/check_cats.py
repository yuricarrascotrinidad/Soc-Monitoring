import sqlite3

def check_alarms():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    
    print("Checking unique alarm names for BATERIA BAJA category:")
    cur = conn.execute("SELECT DISTINCT alarma FROM alarmas WHERE categoria = 'BATERIA BAJA'")
    for row in cur.fetchall():
        print(f" - {row['alarma']}")
        
    print("\nChecking if 'interruption' alarms exist in the DB:")
    cur = conn.execute("SELECT DISTINCT alarma, categoria FROM alarmas WHERE alarma LIKE '%interruption%'")
    for row in cur.fetchall():
        print(f" - {row['alarma']} (Category: {row['categoria']})")
        
    conn.close()

if __name__ == "__main__":
    check_alarms()
