
import os
import sys
from datetime import datetime

# Mock Flask components
class MockBlueprint:
    def route(self, *args, **kwargs):
        return lambda x: x

class MockJWT:
    def __call__(self):
        return lambda x: x

sys.modules['flask'] = type('MockFlask', (), {'Blueprint': MockBlueprint, 'jsonify': lambda x: x, 'request': type('MockReq', (), {'args': {}})})
sys.modules['flask_jwt_extended'] = type('MockJWTEx', (), {'jwt_required': MockJWT(), 'get_jwt': lambda: {"permissions": {"view_batteries": True}}})

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.routes.api import get_ac_data
from app.utils.db import query_db

def verify():
    print("--- Verifying API Changes ---")
    
    # Simular una respuesta de la API (mockeando internamente si es necesario, 
    # pero aquí podemos llamar a la función real si la DB está disponible)
    try:
        response = get_ac_data()
        records = response.get("records", [])
        
        found_tarucani = False
        for r in records:
            if r["sitio"] == "T1045_AR_TARUCANI":
                found_tarucani = True
                print(f"Site: {r['sitio']}")
                print(f"  Voltaje display: {r['voltaje']}")
                print(f"  Svoltaje site-level: {r['svoltaje']}")
                
                if r["baterias"]:
                    b = r["baterias"][0]
                    print(f"  Battery info: {b['nombre']}")
                    print(f"    Fields present: {'voltaje' in b}, {'svoltaje' in b}, {'current1' in b}")
                    if 'voltaje' in b:
                        print(f"    Values: Volt={b['voltaje']}, SVolt={b['svoltaje']}, Cur1={b['current1']}")
                
                if r["voltaje"] != "N/A":
                    print("✅ T1045_AR_TARUCANI no longer shows N/A.")
                else:
                    print("❌ T1045_AR_TARUCANI still shows N/A.")
        
        if not found_tarucani:
            print("⚠️ Site T1045_AR_TARUCANI not found in active alarms.")
            
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
