from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarmas_historicas'")
print("HIST_COLUMNS:")
for r in cur.fetchall():
    print(f"  {r[0]}")
cur.execute("""
    SELECT conname, pg_get_constraintdef(oid) 
    FROM pg_constraint 
    WHERE conrelid = 'alarmas_historicas'::regclass
""")
print("HIST_CONSTRAINTS:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn.close()
