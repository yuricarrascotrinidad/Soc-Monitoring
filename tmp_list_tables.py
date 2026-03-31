import psycopg2
from app.config import Config
import io

def list_tables():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('information_schema', 'pg_catalog')")
    tables = cur.fetchall()
    
    with io.open('tmp_tables_list.txt', 'w', encoding='utf-8') as f:
        for t in tables:
            f.write(f"Schema: {t[0]}, Table: {t[1]}\n")
    conn.close()

if __name__ == '__main__':
    list_tables()
