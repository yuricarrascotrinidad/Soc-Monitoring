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
        print("Intentando eliminar columna 'conexion' de 'battery_telemetry'...")
        cur.execute("ALTER TABLE battery_telemetry DROP COLUMN IF EXISTS conexion;")
        conn.commit()
        print("✅ Columna eliminada exitosamente (o no existía).")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    migrate()
