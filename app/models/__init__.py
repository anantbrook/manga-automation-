from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models here so that db.create_all() detects them
# and SQLAlchemy relationship mappers resolve string references correctly.
from app.models.manga import Manga
from app.models.chapter import Chapter
from app.models.subscription import Subscription
from app.models.scraper import ScraperHealth
from app.models.user import User, Bookmark, ReadingHistory
