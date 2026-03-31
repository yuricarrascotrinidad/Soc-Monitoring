from app.utils.db import get_db_connection
import json
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT name, permissions FROM roles")
roles_data = cur.fetchall()
for name, perms in roles_data:
    print(f"ROLE: {name}")
    print(f"PERMS: {json.dumps(perms, indent=2)}")
conn.close()
