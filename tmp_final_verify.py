import psycopg2
import psycopg2.extras
from app.config import Config

def check_db():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT count(*) FROM alarmas_activas")
    print(f"Total active alarms: {cur.fetchone()['count']}")
    
    print("\n--- Any Remaining Duplicates? (Same site/alarm/time, different device_id) ---")
    cur.execute("""
        SELECT sitio, alarma, hora, count(*) as cnt
        FROM alarmas_activas
        GROUP BY sitio, alarma, hora
        HAVING count(*) > 1
        LIMIT 10
    """)
    rows = cur.fetchall()
    if not rows:
        print("🎉 No duplicates found!")
    else:
        for row in rows:
            print(f"Site: {row['sitio']}, Alm: {row['alarma']}, Time: {row['hora']}, Count: {row['cnt']}")

    print("\n--- Alarms with AC-related names but NOT categorized as AC_FAIL ---")
    cur.execute("""
        SELECT DISTINCT alarma, devicename, categoria, count(*) as cnt
        FROM alarmas_activas
        WHERE (alarma ILIKE '%falla%red%' OR alarma ILIKE '%mains%failure%' OR alarma ILIKE '%falla%red%' OR alarma ILIKE '%voltaje fase%')
        AND categoria != 'AC_FAIL'
        GROUP BY alarma, devicename, categoria
    """)
    rows = cur.fetchall()
    if not rows:
        print("🎉 All AC-related alarms are correctly categorized as AC_FAIL!")
    else:
        for row in rows:
            print(row)

    print("\n--- Latest 5 Alarms (Verifying source) ---")
    cur.execute("SELECT id, sitio, alarma, categoria, source, hora FROM alarmas_activas ORDER BY id DESC LIMIT 5")
    for row in cur.fetchall():
        print(row)

    conn.close()

if __name__ == '__main__':
    check_db()
