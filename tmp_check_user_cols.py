from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
print("USER_COLUMNS:")
for r in cur.fetchall():
    print(f"  {r[0]}")
conn.close()
