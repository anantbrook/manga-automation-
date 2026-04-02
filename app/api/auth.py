from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import bcrypt
from datetime import datetime, timedelta
from app.models import db
from app.models.user import User, Bookmark, ReadingHistory
from app.models.manga import Manga
from app.core.config import Config

auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            current_user = db.session.get(User, data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except Exception:
            return jsonify({'error': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=username, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }, Config.SECRET_KEY, algorithm="HS256")

    return jsonify({'token': token, 'username': user.username}), 200

@user_bp.route('/bookmarks', methods=['GET'])
@token_required
def get_bookmarks(current_user):
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
    results = []
    for b in bookmarks:
        manga = db.session.get(Manga, b.manga_id)
        if manga:
            cover = f"/api/manga/proxy-image?url={manga.cover_url}" if manga.cover_url else ""
            results.append({
                "id": manga.id,
                "title": manga.title,
                "cover_url": cover,
                "source": manga.source
            })
    return jsonify(results)

@user_bp.route('/bookmarks', methods=['POST'])
@token_required
def add_bookmark(current_user):
    data = request.get_json()
    manga_id = data.get('manga_id')

    if not manga_id:
        return jsonify({'error': 'manga_id required'}), 400

    existing = Bookmark.query.filter_by(user_id=current_user.id, manga_id=manga_id).first()
    if existing:
        return jsonify({'message': 'Already bookmarked'}), 200

    new_bookmark = Bookmark(user_id=current_user.id, manga_id=manga_id)
    db.session.add(new_bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmarked successfully'}), 201

@user_bp.route('/bookmarks/<path:manga_id>', methods=['DELETE'])
@token_required
def remove_bookmark(current_user, manga_id):
    bookmark = Bookmark.query.filter_by(user_id=current_user.id, manga_id=manga_id).first()
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
    return jsonify({'message': 'Bookmark removed'}), 200

@user_bp.route('/history', methods=['POST'])
@token_required
def update_history(current_user):
    data = request.get_json()
    manga_id = data.get('manga_id')
    chapter_id = data.get('chapter_id')

    if not manga_id or not chapter_id:
        return jsonify({'error': 'manga_id and chapter_id required'}), 400

    history = ReadingHistory.query.filter_by(user_id=current_user.id, manga_id=manga_id).first()
    if history:
        history.chapter_id = chapter_id
        history.last_read_at = datetime.utcnow()
    else:
        history = ReadingHistory(user_id=current_user.id, manga_id=manga_id, chapter_id=chapter_id)
        db.session.add(history)

    db.session.commit()
    return jsonify({'message': 'History updated'}), 200

@user_bp.route('/history', methods=['GET'])
@token_required
def get_history(current_user):
    history = ReadingHistory.query.filter_by(user_id=current_user.id).order_by(ReadingHistory.last_read_at.desc()).limit(20).all()
    results = []
    for h in history:
        manga = db.session.get(Manga, h.manga_id)
        if manga:
            cover = f"/api/manga/proxy-image?url={manga.cover_url}" if manga.cover_url else ""
            results.append({
                "manga_id": manga.id,
                "title": manga.title,
                "cover_url": cover,
                "last_read_chapter": h.chapter_id.split('/')[-1],
                "last_read_at": h.last_read_at.isoformat()
            })
    return jsonify(results)
