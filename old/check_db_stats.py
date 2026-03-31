
import sqlite3

def check_db():
    conn = sqlite3.connect('monitoring.db')
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM alarmas;")
    count = cur.fetchone()[0]
    print(f"Total rows in alarmas: {count}")
    
    cur.execute("PRAGMA table_info(alarmas);")
    columns = cur.fetchall()
    print("\nColumns in alarmas:")
    for col in columns:
        print(col)
        
    cur.execute("PRAGMA index_list(alarmas);")
    indexes = cur.fetchall()
    print("\nIndexes on alarmas:")
    for idx in indexes:
        print(idx)
        cur.execute(f"PRAGMA index_info({idx[1]});")
        print(cur.fetchall())
        
    conn.close()

if __name__ == "__main__":
    check_db()
