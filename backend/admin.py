from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import hashlib
from datetime import datetime, timedelta
from model import client  #✅FIXED: models (plural)

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
    # ✅ FIXED: Use scroll (returns tuple of [points, offset])
    points, _ = client.scroll(collection_name="chat_logs", limit=100)
    
    logs = [{
        'id': str(point.id),
        'timestamp': point.payload.get('timestamp'),
        'session_id': point.payload.get('session_id'),
        'question': point.payload.get('question'),
        'answer': point.payload.get('answer'),
        'response_time': point.payload.get('response_time', 0),
        'sources': point.payload.get('sources', 0)
    } for point in points]
    
    # Sort by timestamp descending (Newest first: 25th, 24th, 23rd...)
    logs.sort(key=lambda x: x.get('timestamp') or "", reverse=True)
    
    return jsonify({
        'logs': logs,
        'total': len(logs),
        'admin': username
    })
