import os

class Config:
    # Database
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'monitoring.db')
    
    # PostgreSQL Database
    PG_HOST = os.environ.get('PG_HOST') or 'localhost'
    PG_PORT = os.environ.get('PG_PORT') or '5432'
    PG_DATABASE = os.environ.get('PG_DATABASE') or 'monitoring'
    PG_USER = os.environ.get('PG_USER') or 'postgres'
    PG_PASSWORD = os.environ.get('PG_PASSWORD') or 'yofc'
    
    # Camera Resources
    RECURSOS_DIR = os.path.join(BASE_DIR, 'recursos')
    EXCEL_FILE_ACCESS = os.path.join(RECURSOS_DIR, 'access.xlsx')
    EXCEL_FILE_TRANSPORT = os.path.join(RECURSOS_DIR, 'transport.xlsx')

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_secreta_por_defecto'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or '9d7a3e5c1f4b8a2d6e9c0b7f3a1e5d8c2f6a4b9e0d7c1a3f5e8b2c6d9a0f4e7'
    JWT_ACCESS_TOKEN_EXPIRES = 86400 # 1 day
    
    # Email Config
    EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS') or 'yofcperu123@gmail.com'
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') or 'sazj wjig emhk fsbj'
    EMAIL_DESTIANTION = os.environ.get('EMAIL_DESTIMATION') or 'yuri.trinidad@yofc.com'
    
    # PEIM Credentials
    PEIM_USER = os.environ.get('PEIM_USER') or 'noc_reports'
    PEIM_PASS = os.environ.get('PEIM_PASS') or 'N0c!oficina#'
    
    # Camera Credentials
    CAMERA_USER = os.environ.get('CAMERA_USER') or 'admin'
    CAMERA_PASSWORD = os.environ.get('CAMERA_PASSWORD') or 'Yofc12345'
    CAMERA_PASSWORDS = [
        CAMERA_PASSWORD,
        'Yofc1245',
        'yofc123456'
    ]
