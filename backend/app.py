import os
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from models import db

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    CORS(app)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

    # Use Postgres in Docker, fallback to SQLite locally
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///manga.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Register Blueprints
    from routes.api import api_bp
    from routes.admin import admin_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5000, host='0.0.0.0')