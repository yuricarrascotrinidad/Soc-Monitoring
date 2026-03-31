from app.utils.db import get_db_connection
import json
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT name, permissions FROM roles")
print("ROLES:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
conn.close()
