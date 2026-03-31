import sqlite3
import os
import time
from datetime import datetime, timedelta

db_path = 'monitoring.db'

def run_optimization():
    print(f"--- Starting Optimization for {db_path} ---")
    conn = sqlite3.connect(db_path, timeout=60)
    try:
        conn.execute("PRAGMA busy_timeout=60000")
        
        print("1. Applying Performance Indexes...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_dashboard_v2 ON alarmas (tipo, hora, estado)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_pruning_v2 ON alarmas (hora, estado)")
        conn.commit()
        
        print("2. Verifying Stale Records...")
        ahora = datetime.now()
        limite_7d = (ahora - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cur = conn.execute("DELETE FROM alarmas WHERE hora < ?", (limite_7d,))
            print(f"   - Deleted {cur.rowcount} stale records.")
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"   - Deletion skipped (locked), proceeding to VACUUM: {e}")

        conn.close()
        
        print("3. Executing VACUUM (This might take a minute)...")
        # VACUUM needs autocommit
        conn = sqlite3.connect(db_path, isolation_level=None, timeout=120)
        conn.execute("PRAGMA busy_timeout=120000")
        conn.execute("VACUUM")
        print("   - VACUUM complete.")
        conn.close()
        
        print("4. Finalizing WAL Truncate...")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        size = os.path.getsize(db_path) / (1024*1024)
        print(f"\nOptimization complete. New DB Size: {size:.2f} MB")

    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        if 'conn' in locals() and conn: conn.close()

if __name__ == "__main__":
    run_optimization()
