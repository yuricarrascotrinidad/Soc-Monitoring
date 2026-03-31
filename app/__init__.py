from flask import Flask
from .config import Config
from flask_jwt_extended import JWTManager

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config_class)

    jwt = JWTManager(app)

    # Initialize Blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.video import video_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(auth_bp)

    return app
