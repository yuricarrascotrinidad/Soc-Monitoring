
import os
import sys

# Add the current directory to sys.path to import app modules
sys.path.append(os.getcwd())

from app.utils.db import query_db

def run_research():
    print("--- TABLES ---")
    tables = query_db("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    for t in tables:
        print(t)

    print("\n--- alarmas_activas schema ---")
    cols = query_db("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'alarmas_activas'")
    for c in cols:
        print(c)

    print("\n--- battery_telemetry schema ---")
    cols = query_db("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'battery_telemetry'")
    for c in cols:
        print(c)

    print("\n--- Constraints on alarmas_activas ---")
    cons = query_db("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'alarmas_activas'::regclass")
    for con in cons:
        print(con)

if __name__ == "__main__":
    try:
        run_research()
    except Exception as e:
        print(f"Error: {e}")
