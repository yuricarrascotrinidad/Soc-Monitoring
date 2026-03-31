import sqlite3

def check_duplicates():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    
    # Check for multiple active BATERIA BAJA alerts per device_id
    query = """
    SELECT device_id, sitio, COUNT(*) as c 
    FROM alarmas 
    WHERE estado = 'on' AND categoria = 'BATERIA BAJA' 
    GROUP BY device_id, sitio 
    HAVING c > 1
    """
    
    cur = conn.execute(query)
    rows = cur.fetchall()
    print(f"Devices with multiple active BATERIA BAJA alerts: {len(rows)}")
    for row in rows[:10]:
        print(dict(row))
        
    # Check if a device has both BATERIA and BATERIA BAJA
    query_cross = """
    SELECT device_id, sitio, categoria, COUNT(*) 
    FROM alarmas 
    WHERE estado = 'on' AND device_id IN (SELECT device_id FROM alarmas WHERE categoria = 'BATERIA BAJA' AND estado = 'on')
    GROUP BY device_id, sitio, categoria
    """
    # cur = conn.execute(query_cross)
    # ...
    
    conn.close()

if __name__ == "__main__":
    check_duplicates()
