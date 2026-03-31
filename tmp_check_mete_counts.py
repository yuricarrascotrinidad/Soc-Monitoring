import psycopg2
import psycopg2.extras
from app.config import Config

def check_counts():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT mete_name, count(*) as cnt FROM alarmas_activas WHERE categoria = 'AC_FAIL' GROUP BY mete_name")
    for row in cur.fetchall():
        print(f"{row['mete_name']}: {row['cnt']}")
    conn.close()

if __name__ == '__main__':
    check_counts()
