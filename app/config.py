import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    # Database
    BASE_DIR = BASE_DIR
    DB_PATH = os.path.join(BASE_DIR, os.environ.get('DB_FILENAME'))
    
    # PostgreSQL Database
    PG_HOST = os.environ.get('PG_HOST')
    PG_PORT = os.environ.get('PG_PORT')
    PG_DATABASE = os.environ.get('PG_DATABASE')
    PG_USER = os.environ.get('PG_USER')
    PG_PASSWORD = os.environ.get('PG_PASSWORD')
    
    # Camera Resources
    RECURSOS_DIR = os.path.join(BASE_DIR, os.environ.get('RECURSOS_DIR_NAME'))
    EXCEL_FILE_ACCESS = os.path.join(RECURSOS_DIR, os.environ.get('EXCEL_ACCESS_NAME'))
    EXCEL_FILE_TRANSPORT = os.path.join(RECURSOS_DIR, os.environ.get('EXCEL_TRANSPORT_NAME'))

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    
    # Convert string from env back to int
    try:
        JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES'))
    except (ValueError, TypeError):
        JWT_ACCESS_TOKEN_EXPIRES = 86400
    
    # Email Config
    EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_DESTIANTION = os.environ.get('EMAIL_DESTINATION')
    
    # PEIM Credentials
    PEIM_USER = os.environ.get('PEIM_USER')
    PEIM_PASS = os.environ.get('PEIM_PASS')
    
    # Camera Credentials
    CAMERA_USER = os.environ.get('CAMERA_USER')
    CAMERA_PASSWORD = os.environ.get('CAMERA_PASSWORD')
    
    _cam_passwords_str = os.environ.get('CAMERA_PASSWORDS')
    if _cam_passwords_str:
        CAMERA_PASSWORDS = [p.strip() for p in _cam_passwords_str.split(',')]
    else:
        CAMERA_PASSWORDS = [CAMERA_PASSWORD]
