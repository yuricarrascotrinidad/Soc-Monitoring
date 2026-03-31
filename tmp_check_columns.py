import psycopg2
from app.config import Config
import io

def check_columns():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarmas_activas'")
    cols = cur.fetchall()
    
    with io.open('tmp_columns_list.txt', 'w', encoding='utf-8') as f:
        for c in cols:
            f.write(f"{c[0]}\n")
    conn.close()

if __name__ == '__main__':
    check_columns()
