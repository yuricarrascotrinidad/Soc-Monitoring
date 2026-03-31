import psycopg2
from app.config import Config
import io

def check_indices():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT
            i.relname as index_name,
            a.attname as column_name,
            ix.indisunique as is_unique,
            ix.indisprimary as is_primary
        FROM
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        WHERE
            t.oid = ix.indrelid
            AND i.oid = ix.indexrelid
            AND a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
            AND t.relname = 'battery_telemetry'
        ORDER BY
            i.relname
    """)
    indices = cur.fetchall()
    
    with io.open('tmp_indices_utf8.txt', 'w', encoding='utf-8') as f:
        for idx in indices:
            f.write(f"Index: {idx[0]}, Col: {idx[1]}, Unique: {idx[2]}, Primary: {idx[3]}\n")
    conn.close()

if __name__ == '__main__':
    check_indices()
