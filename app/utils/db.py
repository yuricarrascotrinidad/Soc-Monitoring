import sqlite3
import psycopg2
from psycopg2 import extras
from flask import current_app, g
from app.config import Config

def get_db_connection():
    """
    Retorna una conexión a la base de datos. 
    Actualmente configurado para PostgreSQL.
    """
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Error conectando a PostgreSQL: {e}")
        # Caer en SQLite como fallback o manejar el error
        raise e

def get_sqlite_connection():
    # Use timeout to wait for locks and WAL mode for concurrent read/write
    conn = sqlite3.connect(Config.DB_PATH, timeout=60.0)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    try:
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        cur.close()
        conn.close()

def execute_db(query, args=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        last_id = None
        try:
            # PostgreSQL doesn't have lastrowid like SQLite
            # This is a generic approach; specific tables might need RETURNING id
            if "INSERT" in query.upper():
                 pass # Depende de la implementación específica si se necesita el ID
        except: pass
        cur.close()
        return last_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
