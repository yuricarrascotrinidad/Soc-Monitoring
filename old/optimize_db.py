import sqlite3
import os
import time

DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')

def optimize_database():
    print(f"Connecting to database at {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        print("Creating indexes...")
        # Create indexes for 'alarmas' table
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_region_estado ON alarmas(tipo, region, estado)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_hora ON alarmas(hora)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_sitio ON alarmas(sitio)")
        
        # Create indexes for 'notificaciones_enviadas' table
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_sitio_sistema ON notificaciones_enviadas(sitio, tipo_sistema)")
        
        conn.commit()
        print("Indexes created successfully.")
        
        print("Performing VACUUM to reclaim space and reduce WAL size...")
        # VACUUM cannot be run within a transaction, but we just committed.
        # It requires no active transaction.
        conn.execute("VACUUM")
        print("VACUUM completed.")
        
        print("Performing WAL Checkpoint...")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print("WAL Checkpoint completed.")
        
        conn.close()
        print("Database optimization finished successfully.")
        
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        if "locked" in str(e):
            print("The database is locked. Please ensure the application is STOPPED before running this script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    optimize_database()
