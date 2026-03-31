import sqlite3
import threading
import time
import os
from datetime import datetime

DB_PATH = 'monitoring.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    return conn

def actualizar_telemetria_bateria_batch_ORIGINAL(batch_data):
    """Original faulty logic with race condition"""
    if not batch_data:
        return
        
    conn = get_db_connection()
    try:
        with conn:
            for device_id, valores, sitio, nombre in batch_data:
                cur = conn.cursor()
                # READ
                cur.execute("SELECT device_id FROM battery_telemetry WHERE device_id = ?", (device_id,))
                exists = cur.fetchone()
                
                # Race condition: Two threads might see exists=None and both try to INSERT
                # time.sleep(0.1) # Simulate delay to increase race chance
                
                if exists:
                    cur.execute("""
                        UPDATE battery_telemetry 
                        SET soc=?, carga=?, descarga=?, voltaje=?, ultimo_update=?, sitio=?, nombre=?
                        WHERE device_id=?
                    """, (valores['soc'], valores['carga'], valores['descarga'], valores['voltaje'],
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sitio, nombre, device_id))
                else:
                    # WRITE - Might fail with UNIQUE constraint if another thread committed already
                    cur.execute("""
                        INSERT INTO battery_telemetry (device_id, soc, carga, descarga, voltaje, ultimo_update, sitio, nombre)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (device_id, valores['soc'], valores['carga'], valores['descarga'], valores['voltaje'],
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sitio, nombre))
    except Exception as e:
        print(f"Error (EXPECTED): {e}")
        raise e
    finally:
        conn.close()

def thread_task(device_id):
    valores = {'soc': 50, 'carga': 0, 'descarga': 0, 'voltaje': 48}
    try:
        actualizar_telemetria_bateria_batch_ORIGINAL([(device_id, valores, "TestSite", "TestName")])
    except:
        pass

def reproduce():
    # Clean up first
    conn = get_db_connection()
    conn.execute("DELETE FROM battery_telemetry WHERE device_id LIKE 'REPRO-%'")
    conn.commit()
    conn.close()
    
    device_id = "REPRO-001"
    
    # Start two threads at the same time for the same NEW device_id
    t1 = threading.Thread(target=thread_task, args=(device_id,))
    t2 = threading.Thread(target=thread_task, args=(device_id,))
    
    print("Starting reproduction threads...")
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print("Reproduction complete.")

if __name__ == "__main__":
    reproduce()
