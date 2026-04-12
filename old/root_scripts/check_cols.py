
import os
import sys
sys.path.append(os.getcwd())
from app.utils.db import query_db

def check():
    print("BATTERY TELEMETRY COLS:")
    cols = query_db("SELECT column_name FROM information_schema.columns WHERE table_name = 'battery_telemetry'")
    for c in cols:
        print(c['column_name'])
    
    print("\nALARMAS ACTIVAS COLS:")
    cols = query_db("SELECT column_name FROM information_schema.columns WHERE table_name = 'alarmas_activas'")
    for c in cols:
        print(c['column_name'])

if __name__ == "__main__":
    check()
