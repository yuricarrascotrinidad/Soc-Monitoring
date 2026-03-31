
import sqlite3
import time
from datetime import datetime, timedelta

def verify_performance():
    conn = sqlite3.connect('monitoring.db')
    cur = conn.cursor()
    
    db_type = 'access'
    ahora = datetime.now()
    limite_filtro = (ahora - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
    
    print("Testing 'obtener_eventos_cumplidos' query performance...")
    start = time.time()
    cur.execute("""
        SELECT sitio, categoria, estado, alarma, alarmameta, hora, duracion, region
        FROM alarmas
        WHERE tipo = ? AND hora >= ?
        ORDER BY hora ASC
    """, (db_type, limite_filtro))
    rows = cur.fetchall()
    end = time.time()
    print(f"Query returned {len(rows)} rows in {end - start:.4f} seconds.")
    
    print("\nTesting 'anomalias' query performance...")
    start = time.time()
    cur.execute("""
        SELECT sitio, categoria, alarma, alarmameta, COUNT(*) as repeticiones
        FROM alarmas
        WHERE tipo=? AND hora >= ?
        GROUP BY sitio, categoria, alarma, alarmameta
        HAVING repeticiones > 5
    """, (db_type, limite_filtro))
    anoms = cur.fetchall()
    end = time.time()
    print(f"Anomalies query returned {len(anoms)} results in {end - start:.4f} seconds.")
    
    conn.close()

if __name__ == "__main__":
    verify_performance()
