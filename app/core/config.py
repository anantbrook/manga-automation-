import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret')
    # Use PostgreSQL if provided, else fallback to sqlite for local dev ease if not strictly required,
    # but the requirement is PostgreSQL via SQLAlchemy.
    # Defaulting to PostgreSQL assuming it is configured via DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mangafire')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin123')
