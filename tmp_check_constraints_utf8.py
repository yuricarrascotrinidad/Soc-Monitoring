import psycopg2
from app.config import Config
import io

def check_constraints():
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
            conname as constraint_name, 
            pg_get_constraintdef(c.oid) as constraint_definition
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'battery_telemetry'
        AND contype IN ('p', 'u')
    """)
    constraints = cur.fetchall()
    
    with io.open('tmp_constraints_utf8.txt', 'w', encoding='utf-8') as f:
        for con in constraints:
            f.write(f"Constraint: {con[0]}, Def: {con[1]}\n")
    conn.close()

if __name__ == '__main__':
    check_constraints()
