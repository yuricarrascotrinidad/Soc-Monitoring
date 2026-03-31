import psycopg2
from app.config import Config

def check_types():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT tipo_dispositivo FROM catalogo_dispositivos WHERE activo = TRUE;")
    types = [row[0] for row in cur.fetchall()]
    print(f"Active device types: {types}")
    conn.close()

if __name__ == "__main__":
    check_types()
