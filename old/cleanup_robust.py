import sqlite3
import os
from datetime import datetime, timedelta
import time

DB_PATH = 'monitoring.db'
CHUNK_SIZE = 50000

def cleanup_in_chunks():
    print(f"Iniciando limpieza robusta en {DB_PATH} por fragmentos de {CHUNK_SIZE}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Base de datos no encontrada en {DB_PATH}")
        return

    # Calcular límite de 24 horas
    ahora = datetime.now()
    limite = (ahora - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Límite de tiempo: {limite}")

    try:
        conn = sqlite3.connect(DB_PATH, timeout=300)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        cur = conn.cursor()
        
        # Contar total inicial
        cur.execute("SELECT COUNT(*) FROM alarmas WHERE hora < ? AND estado != 'on'", (limite,))
        total_inicial = cur.fetchone()[0]
        
        if total_inicial == 0:
            print("No hay registros antiguos para borrar.")
            conn.close()
            return

        print(f"Total de registros a eliminar: {total_inicial}")
        
        eliminados_total = 0
        while True:
            # Borrar en fragmentos para evitar bloqueos masivos y errores de E/S
            cur.execute(f"""
                DELETE FROM alarmas 
                WHERE id IN (
                    SELECT id FROM alarmas 
                    WHERE hora < ? AND estado != 'on' 
                    LIMIT {CHUNK_SIZE}
                )
            """, (limite,))
            
            count = cur.rowcount
            if count == 0:
                break
                
            conn.commit()
            eliminados_total += count
            print(f"Progreso: {eliminados_total}/{total_inicial} eliminados...")
            time.sleep(0.5) # Breve pausa para permitir otros accesos

        print(f"Eliminación finalizada. Total eliminados: {eliminados_total}")

        # Compactar solo si se borró mucho
        if eliminados_total > 50000:
            print("Ejecutando VACUUM para recuperar espacio. Esto puede tardar...")
            start_v = time.time()
            conn.execute("VACUUM")
            print(f"VACUUM completado en {time.time() - start_v:.2f}s")

        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        final_size = os.path.getsize(DB_PATH) / (1024 * 1024)
        print(f"Limpieza completa. Tamaño final: {final_size:.2f} MB")
        
        conn.close()

    except Exception as e:
        print(f"Error durante la limpieza: {e}")

if __name__ == "__main__":
    cleanup_in_chunks()
