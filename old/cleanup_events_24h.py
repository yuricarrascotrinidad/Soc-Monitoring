import sqlite3
import os
from datetime import datetime, timedelta
import time

DB_PATH = 'monitoring.db'

def cleanup_events_24h_refined():
    print(f"Iniciando limpieza global de registros (>24h) en {DB_PATH}...")
    print("Nota: Se conservarán todos los registros en estado 'on' sin importar su antigüedad.")
    
    if not os.path.exists(DB_PATH):
        print(f"Base de datos no encontrada en {DB_PATH}")
        return

    # Calcular límite de 24 horas
    ahora = datetime.now()
    limite = (ahora - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Límite de tiempo: {limite}")

    try:
        # Conexión con timeout generoso
        conn = sqlite3.connect(DB_PATH, timeout=300)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        cur = conn.cursor()
        
        # 1. Contar registros que cumplen el criterio de borrado
        cur.execute("""
            SELECT COUNT(*) 
            FROM alarmas 
            WHERE hora < ? AND estado != 'on'
        """, (limite,))
        
        total_a_borrar = cur.fetchone()[0]
        
        if total_a_borrar == 0:
            print("No se encontraron registros antiguos (no activos) para limpiar.")
            conn.close()
            return

        print(f"Registros a eliminar: {total_a_borrar}")

        # 2. Ejecutar eliminación
        print("Eliminando registros...")
        start_del = time.time()
        cur.execute("""
            DELETE FROM alarmas 
            WHERE hora < ? AND estado != 'on'
        """, (limite,))
        
        deleted_count = cur.rowcount
        conn.commit()
        end_del = time.time()
        print(f"Eliminación completada en {end_del - start_del:.2f} segundos. Eliminados: {deleted_count}")

        # 3. VACUUM si se eliminaron muchos registros (>50,000)
        if deleted_count > 50000:
            print("Realizando VACUUM para compactar la base de datos (9GB+). Esto puede tardar...")
            start_vacuum = time.time()
            conn.execute("VACUUM")
            end_vacuum = time.time()
            print(f"VACUUM completado en {end_vacuum - start_vacuum:.2f} segundos.")
        
        # 4. Checkpoint
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        # 5. Tamaño final
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
        print(f"Limpieza finalizada con éxito. Tamaño actual de DB: {db_size:.2f} MB")

        conn.close()

    except sqlite3.OperationalError as e:
        print(f"Error operativo: {e}")
        if "locked" in str(e):
            print("LA BASE DE DATOS ESTÁ BLOQUEADA. Asegúrate de detener el servicio de monitoreo.")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    cleanup_events_24h_refined()
