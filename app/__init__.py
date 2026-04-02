import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.core.config import Config
from app.models import db
from app.api import api_bp
from app.admin.routes import admin_bp
from app.core.celery_app import make_celery
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    os.makedirs(os.path.join(base_dir, 'static', 'manga'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'static', 'dist'), exist_ok=True)

    db.init_app(app)
    migrate = Migrate(app, db)

    # Re-add rate limiting as requested by review
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    app.celery = make_celery(app)

    with app.app_context():
        db.create_all()

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        dist_dir = os.path.join(base_dir, 'static', 'dist')
        static_dir = os.path.join(base_dir, 'static')

        if path.startswith('static/'):
            file_path = path.replace('static/', '', 1)
            return send_from_directory(static_dir, file_path)

        if path != "" and os.path.exists(os.path.join(dist_dir, path)):
            return send_from_directory(dist_dir, path)

        return send_from_directory(dist_dir, 'index.html')

    return app
