import sqlite3
import os
from datetime import datetime, timedelta

# Mock Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'monitoring.db')

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to database at {DB_PATH}: {e}")
        return None

def obtener_anomalias(db_type):
    conn = get_db_connection()
    if not conn:
        return []
        
    cur = conn.cursor()
    
    # Use system time as we don't know exact server time, but it should be close enough
    ahora = datetime.now()
    limite_24h = ahora - timedelta(hours=24)
    limite_str = limite_24h.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Checking {db_type} anomalies since: {limite_str}")
    
    anomalias = []
    try:
        # 1. Get Distinct Sites/Categories
        query1 = """
            SELECT DISTINCT sitio, categoria 
            FROM alarmas 
            WHERE tipo = ? AND hora >= ?
        """
        cur.execute(query1, (db_type, limite_str))
        sitios_categorias = cur.fetchall()
        print(f"Found {len(sitios_categorias)} distinct site/category pairs.")

        for row in sitios_categorias:
            sitio = row['sitio']
            categoria = row['categoria']
            
            # 2. Get Alarms > 5 reps
            query2 = """
                SELECT alarma, alarmameta, COUNT(*) as repeticiones
                FROM alarmas
                WHERE tipo=? AND sitio=? AND categoria=? AND hora >= ?
                GROUP BY alarma, alarmameta
                HAVING repeticiones > 5
            """
            cur.execute(query2, (db_type, sitio, categoria, limite_str))
            
            rows = cur.fetchall()
            if rows:
                print(f"  Site: {sitio}, Cat: {categoria} -> {len(rows)} anomalies found.")
                for r in rows:
                    print(f"    - Alarm: {r['alarma']}, Meta: {r['alarmameta']}, Reps: {r['repeticiones']}")
                    
                    anomalias.append({
                        "sitio": sitio,
                        "categoria": categoria,
                        "alarma": r['alarma'],
                        "alarmameta": r['alarmameta'],
                        "veces": r['repeticiones']
                    })
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()
        
    return anomalias

if __name__ == "__main__":
    print("--- Access Anomalies ---")
    access_anomalies = obtener_anomalias("access")
    print(f"\nTotal Access Anomalies: {len(access_anomalies)}")

    print("\n--- Transport Anomalies ---")
    transport_anomalies = obtener_anomalias("transport")
    print(f"\nTotal Transport Anomalies: {len(transport_anomalies)}")
