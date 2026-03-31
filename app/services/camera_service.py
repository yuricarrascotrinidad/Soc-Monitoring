import cv2
import time
import socket
import logging
from app.utils.db import get_db_connection
from app.config import Config
from functools import lru_cache

class CameraService:
    @staticmethod
    def check_port(ip, port, timeout=1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    @staticmethod
    @lru_cache(maxsize=128)
    def get_camera_ip(site_name, camera_type="access", position="principal"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if camera_type == "access":
                cursor.execute("SELECT ip FROM access_cameras WHERE site = %s", (site_name,))
            else:
                # Mapear nombres de columnas a positions db
                position_map = {
                    "principal": "prin",
                    "prin": "prin",
                    "patio": "patio",
                    "equipo": "equipo",
                    "generador": "generador"
                }
                db_position = position_map.get(position, position)
                
                cursor.execute("""
                    SELECT ip FROM transport_cameras 
                    WHERE site = %s AND position = %s
                """, (site_name, db_position))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception:
            return None
        finally:
            conn.close()

    @staticmethod
    def get_transport_cameras_for_site(site_name):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT position, ip FROM transport_cameras 
                WHERE site = %s 
            """, (site_name,))
            results = cursor.fetchall()
            
            cameras = {}
            for position, ip in results:
                display_position = {
                    "prin": "principal",
                    "patio": "patio",
                    "equipo": "equipo",
                    "generador": "generador"
                }.get(position, position)
                cameras[display_position] = ip
            return cameras
        finally:
            conn.close()

    @staticmethod
    @lru_cache(maxsize=128)
    def has_camera(site_name, camera_type="access"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if camera_type == "access":
                cursor.execute("SELECT 1 FROM access_cameras WHERE site = %s", (site_name,))
            else:
                cursor.execute("SELECT 1 FROM transport_cameras WHERE site = %s", (site_name,))
            return cursor.fetchone() is not None
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_camera_status(site_name, camera_type="access", position="principal"):
        """
        Check camera configuration status.
        Returns: {"status": "online|no_config", "ip": ip_address, "message": description}
        """
        try:
            # Get camera IP
            ip = CameraService.get_camera_ip(site_name, camera_type, position)
            
            if not ip:
                return {
                    "status": "no_config",
                    "ip": None,
                    "message": "No IP configured"
                }
            
            # If IP exists, consider it online (no ping check)
            return {
                "status": "online",
                "ip": ip,
                "message": "Camera configured"
            }
        except Exception as e:
            logging.error(f"Error checking camera status for {site_name}: {e}")
            return {
                "status": "no_config",
                "ip": None,
                "message": f"Error: {str(e)}"
            }


    @staticmethod
    def get_rtsp_url(ip, user, password):
        return f"rtsp://{user}:{password}@{ip}:554/Streaming/Channels/101"

    @staticmethod
    def generate_frames(site_name, camera_type="access", position="principal"):
        ip = CameraService.get_camera_ip(site_name, camera_type, position)
        
        if not ip:
            yield CameraService._get_error_frame("IP no encontrada")
            return

        if not CameraService.check_port(ip, 554):
             yield CameraService._get_error_frame("Cámara offline")
             return

        cap = None
        current_pass = None
        for password in Config.CAMERA_PASSWORDS:
            rtsp_url = CameraService.get_rtsp_url(ip, Config.CAMERA_USER, password)
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                current_pass = password
                break
            cap.release()

        if not cap or not cap.isOpened():
            yield CameraService._get_error_frame("Error conectando RTSP (Credenciales)")
            return

        # Reducir buffer para latencia mínima
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # Aumentar resolución para evitar pixeleado (HD 720p)
            frame = cv2.resize(frame, (1280, 720))
            
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # Sin sleep para tiempo real

        cap.release()

    @staticmethod
    def _get_error_frame(text):
        try:
            import numpy as np
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(img, text, (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', img)
            return (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except:
            return b''

    @staticmethod
    def capture_snapshot(site_name, camera_type="access", position="principal"):
        ip = CameraService.get_camera_ip(site_name, camera_type, position)
        if not ip: return None
        
        cap = None
        for password in Config.CAMERA_PASSWORDS:
            rtsp_url = CameraService.get_rtsp_url(ip, Config.CAMERA_USER, password)
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                break
            cap.release()
            cap = None

        if not cap or not cap.isOpened(): return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Encode to JPEG bytes
            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    return buffer.tobytes()
            except Exception as e:
                logging.error(f"Error encoding snapshot: {e}")
        return None
