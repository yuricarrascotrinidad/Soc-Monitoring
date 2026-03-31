
import sqlite3
import logging

def apply_optimizations():
    logging.basicConfig(level=logging.INFO)
    conn = sqlite3.connect('monitoring.db')
    try:
        # 1. Create indexes for performance
        logging.info("Creating index on 'hora' column...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_hora ON alarmas (hora);")
        
        logging.info("Creating composite index on (tipo, hora)...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_hora ON alarmas (tipo, hora);")
        
        # 2. Optimize DB
        logging.info("Running VACUUM and ANALYZE...")
        conn.execute("VACUUM;")
        conn.execute("ANALYZE;")
        
        conn.commit()
        logging.info("Database optimizations applied successfully.")
    except Exception as e:
        logging.error(f"Error applying optimizations: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_optimizations()
