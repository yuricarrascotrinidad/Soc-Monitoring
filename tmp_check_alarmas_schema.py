import psycopg2
from app.config import Config

def check_schema():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    print("--- alarmas_activas schema ---")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'alarmas_activas' ORDER BY ordinal_position")
    cols = cur.fetchall()
    for col in cols:
        print(f"Column: {col[0]}, Type: {col[1]}")
    
    print("\n--- unique constraints ---")
    cur.execute("""
        SELECT conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE contype IN ('u', 'p') AND conrelid = 'alarmas_activas'::regclass
    """)
    constraints = cur.fetchall()
    for con in constraints:
        print(f"Constraint: {con[0]}, Def: {con[1]}")
    
    conn.close()

if __name__ == '__main__':
    check_schema()
