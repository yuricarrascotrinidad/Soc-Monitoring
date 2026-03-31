import psycopg2
from app.config import Config

def migrate():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        print("Intentando re-agregar columna 'conexion' a 'battery_telemetry'...")
        cur.execute("ALTER TABLE battery_telemetry ADD COLUMN IF NOT EXISTS conexion INTEGER DEFAULT 0;")
        conn.commit()
        print("✅ Columna agregada exitosamente.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    migrate()
