import sqlite3
import os
import time
from datetime import datetime, timedelta

DB_PATH = 'monitoring.db'

def cleanup_database():
    print(f"Starting aggressive cleanup of {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    # Calculate retention window
    ahora = datetime.now()
    limite_24h = (ahora - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    limite_futuro = (ahora + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Retention policy: Keep records between {limite_24h} and {limite_futuro}, or if status is 'on'")

    try:
        # Increase timeout for this operation
        conn = sqlite3.connect(DB_PATH, timeout=300)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        # 1. Count before
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alarmas")
        count_before = cur.fetchone()[0]
        print(f"Records in 'alarmas' before cleanup: {count_before}")

        # 2. Delete old records
        print(f"Deleting records older than {limite_24h} and NOT 'on'...")
        cur.execute("DELETE FROM alarmas WHERE hora < ? AND estado != 'on'", (limite_24h,))
        deleted_old = cur.rowcount
        print(f"Deleted {deleted_old} old records.")

        # 3. Delete future records (glitches)
        print(f"Deleting records with future dates (>{limite_futuro})...")
        cur.execute("DELETE FROM alarmas WHERE hora > ?", (limite_futuro,))
        deleted_future = cur.rowcount
        print(f"Deleted {deleted_future} future records.")

        # 4. Commit deletions
        conn.commit()
        
        # 5. Shrink database
        print("Performing VACUUM. This may take some time given the 9GB size...")
        start_vacuum = time.time()
        conn.execute("VACUUM")
        end_vacuum = time.time()
        print(f"VACUUM completed in {end_vacuum - start_vacuum:.2f} seconds.")

        # 6. Checkpoint and Truncate WAL
        print("Truncating WAL file...")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        # 7. Count after
        cur.execute("SELECT COUNT(*) FROM alarmas")
        count_after = cur.fetchone()[0]
        print(f"Records in 'alarmas' after cleanup: {count_after}")
        
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
        print(f"Final database size: {db_size:.2f} MB")

        conn.close()
        print("Database cleanup finished successfully.")

    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        if "locked" in str(e):
            print("The database is locked. Please ensure the main application is STOPPED before running this script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    cleanup_database()
