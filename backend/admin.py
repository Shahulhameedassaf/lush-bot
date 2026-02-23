from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import hashlib
from datetime import datetime, timedelta
from model import client

admin_bp = Blueprint('admin', __name__)
SECRET_KEY = "lushbot-secret-key-2026-change-this"

USERS = {
    "admin": hashlib.sha256("lushbot2026".encode()).hexdigest()
}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'error': 'Login required'}), 401
        
        token = auth.split(' ')[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            username = payload['username']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(username=username, *args, **kwargs)
    return decorated

@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    if username in USERS and USERS[username] == hashed:
        token = jwt.encode({
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'username': username})
    return jsonify({'error': 'Wrong credentials'}), 401

@admin_bp.route('/logs', methods=['GET'])
@require_auth
def logs(username):
    results = client.scroll("chat_logs", limit=100)
    logs = [{
        'id': log.id,
        'timestamp': log.payload.get('timestamp'),
        'session_id': log.payload.get('session_id'),
        'question': log.payload.get('question'),
        'answer': log.payload.get('answer'),
        'response_time': log.payload.get('response_time', 0)
    } for log in results[0]]
    
    return jsonify({
        'logs': logs[::-1],  # Newest first
        'total': len(logs),
        'admin': username
    })
