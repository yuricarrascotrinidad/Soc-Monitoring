import psycopg2
import psycopg2.extras
from app.config import Config

def check_alarms():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("--- Alarms with category AC_FAIL ---")
    cur.execute("""
        SELECT DISTINCT mete_name, count(*) 
        FROM alarmas_activas 
        WHERE categoria = 'AC_FAIL' 
        GROUP BY mete_name
    """)
    for row in cur.fetchall():
        print(f"Mete: {row['mete_name']}, Count: {row['count']}")
    
    print("\n--- Alarms with AC-related names but NOT categorized as AC_FAIL ---")
    cur.execute("""
        SELECT DISTINCT alarma, categoria, count(*)
        FROM alarmas_activas
        WHERE (alarma ILIKE '%falla de red%' OR alarma ILIKE '%mains failure%' OR alarma ILIKE '%voltaje fase%')
        AND categoria != 'AC_FAIL'
        GROUP BY alarma, categoria
    """)
    for row in cur.fetchall():
        print(f"Alm: {row['alarma']}, Cat: {row['categoria']}, Count: {row['count']}")

    print("\n--- Duplicate Check (Same site/alarm/time, different device_id) ---")
    cur.execute("""
        SELECT sitio, alarma, hora, count(*)
        FROM alarmas_activas
        GROUP BY sitio, alarma, hora
        HAVING count(*) > 1
        LIMIT 10
    """)
    dups = cur.fetchall()
    for row in dups:
        print(f"Site: {row['sitio']}, Alm: {row['alarma']}, Time: {row['hora']}, Count: {row['count']}")
        # See the device_ids
        cur.execute("SELECT device_id FROM alarmas_activas WHERE sitio=%s AND alarma=%s AND hora=%s", (row['sitio'], row['alarma'], row['hora']))
        ids = [r['device_id'] for r in cur.fetchall()]
        print(f"  IDs: {ids}")

    conn.close()

if __name__ == '__main__':
    check_alarms()
