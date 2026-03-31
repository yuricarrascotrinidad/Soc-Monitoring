import sqlite3

def recategorize_and_cleanup():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    
    print("Standardizing categories strictly...")
    
    # 1. Reset all battery-related categories to allow clean re-categorization
    # conn.execute("UPDATE alarmas SET categoria = 'BATERIA BAJA' WHERE categoria IN ('Bateria', 'BATERIA', 'BATERIA BAJA')")
    
    # 2. SOC-based alerts -> BATERIA BAJA
    print(" - Setting BATERIA BAJA for SOC alarms...")
    conn.execute("""
        UPDATE alarmas 
        SET categoria = 'BATERIA BAJA' 
        WHERE (alarma LIKE '%SOC%' OR alarma LIKE '%BatteryPresentSOCValue%')
    """)
    
    # 3. Hardware/Connection alerts -> Bateria
    print(" - Setting Bateria for interruption alarms...")
    conn.execute("""
        UPDATE alarmas 
        SET categoria = 'Bateria' 
        WHERE (alarma LIKE '%interruption%' OR alarma LIKE '%comunicaci%')
    """)
    
    conn.commit()
    
    # 4. De-duplicate 'on' alarms (keep latest)
    print("Finding redundant 'on' alarms after re-categorization...")
    query = """
    SELECT a.rowid 
    FROM alarmas a
    WHERE a.estado = 'on'
    AND a.rowid NOT IN (
        SELECT MAX(rowid)
        FROM alarmas
        WHERE estado = 'on'
        GROUP BY sitio, device_id, categoria, alarma
    )
    """
    cur = conn.execute(query)
    to_delete = [r[0] for r in cur.fetchall()]
    print(f"Found {len(to_delete)} redundant 'on' alarms.")
    
    if len(to_delete) > 0:
        batch_size = 500
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i+batch_size]
            placeholders = ','.join(['?'] * len(batch))
            conn.execute(f"DELETE FROM alarmas WHERE rowid IN ({placeholders})", batch)
            conn.commit()
            if i % 5000 == 0:
                print(f"Deleted {i} of {len(to_delete)}")
        print(f"Finished deleting {len(to_delete)} rows.")
    
    conn.close()

if __name__ == "__main__":
    recategorize_and_cleanup()
