
import os
import sys
import logging
from datetime import datetime

# Add root to path
sys.path.append(os.getcwd())

from app.services.monitoring_service import MonitoringService
from app.utils.db import get_db_connection, execute_db, query_db

logging.basicConfig(level=logging.INFO)

def test_telemetry_reset():
    sitio_test = "TEST_SITE_REINICIO"
    
    # 1. Limpiar estado previo de prueba
    execute_db("DELETE FROM alarmas_activas WHERE sitio = %s", (sitio_test,))
    execute_db("DELETE FROM battery_telemetry WHERE sitio = %s", (sitio_test,))
    
    # 2. Insertar telemetría ficticia
    execute_db("""
        INSERT INTO battery_telemetry (device_id, sitio, nombre, soc, ultimo_update)
        VALUES ('TEST_DID_001', %s, 'Bateria Test', 80.0, NOW())
    """, (sitio_test,))
    
    print(f"--- Paso 1: Telemetría insertada para {sitio_test} ---")
    res = query_db("SELECT * FROM battery_telemetry WHERE sitio = %s", (sitio_test,))
    print(f"Registros encontrados: {len(res)}")
    
    # 3. Simular llegada de alarma AC_FAIL
    alarmas_mock = [{
        "station_name": sitio_test,
        "alarm_name": "Falla de AC",
        "alarm_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "alarm_span_time": "00:01:00",
        "device_id": "TEST_DID_001",
        "device_name": "Rectificador Test",
        "categoria": "AC_FAIL"
    }]
    
    print(f"\n--- Paso 2: Ejecutando guardar_alarmas con AC_FAIL ---")
    # Nota: el source 'ac' fuerza cat='AC_FAIL' en el código
    MonitoringService.guardar_alarmas('access', alarmas_mock, 'Lima', is_ac=True, source='ac')
    
    # 4. Verificar borrado
    res = query_db("SELECT * FROM battery_telemetry WHERE sitio = %s", (sitio_test,))
    print(f"Registros después de alarma: {len(res)}")
    if len(res) == 0:
        print("✅ ÉXITO: Telemetría borrada correctamente.")
    else:
        print("❌ ERROR: La telemetría NO se borró.")

    # 5. Insertar telemetría de nuevo y re-ejecutar (no debería borrar)
    execute_db("""
        INSERT INTO battery_telemetry (device_id, sitio, nombre, soc, ultimo_update)
        VALUES ('TEST_DID_001', %s, 'Bateria Test New', 75.0, NOW())
    """, (sitio_test,))
    
    print(f"\n--- Paso 3: Re-ejecutando guardar_alarmas con alarma ya existente ---")
    MonitoringService.guardar_alarmas('access', alarmas_mock, 'Lima', is_ac=True, source='ac')
    
    res = query_db("SELECT * FROM battery_telemetry WHERE sitio = %s", (sitio_test,))
    print(f"Registros encontrados: {len(res)}")
    if len(res) > 0:
        print("✅ ÉXITO: La telemetría se mantuvo (no hubo borrado redundante).")
    else:
        print("❌ ERROR: Se borró la telemetría a pesar de ya existir la alarma.")

    # Limpieza final
    execute_db("DELETE FROM alarmas_activas WHERE sitio = %s", (sitio_test,))
    execute_db("DELETE FROM battery_telemetry WHERE sitio = %s", (sitio_test,))

if __name__ == "__main__":
    test_telemetry_reset()
