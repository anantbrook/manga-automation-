import os
import jwt
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash

JWT_SECRET = os.environ.get('JWT_SECRET')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        if not JWT_SECRET:
            return jsonify({'message': 'Server misconfigured. JWT_SECRET missing.'}), 500

        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            from models import User, db
            current_user = db.session.get(User, data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)
    return decorated
