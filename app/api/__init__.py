import os
from flask import Blueprint, jsonify, request
import uuid

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

from app.api.manga import manga_bp
from app.api.chapter import chapter_bp
from app.api.search import search_bp

api_bp.register_blueprint(manga_bp, url_prefix='/manga')
api_bp.register_blueprint(chapter_bp, url_prefix='/chapter')
api_bp.register_blueprint(search_bp, url_prefix='/search')
