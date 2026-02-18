from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM
from datetime import datetime, timedelta
import uuid
import threading
import time
import os
import jwt
import hashlib
# FLASK APP CONFIGURATION
app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend')
CORS(app)
# AUTHENTICATION CONFIGURATION
SECRET_KEY = "lushbot-secret-key-2026-change-this-in-production"

# User credentials (In production, use a proper database!)
# Format: username: hashed_password
USERS = {
    "admin": hashlib.sha256("lushbot2026".encode()).hexdigest(),
    "user": hashlib.sha256("password123".encode()).hexdigest()
}
# LOAD AI MODELS
print("\n" + "="*60)
print("🌿 LUSHBOT SERVER - INITIALIZING")
print("="*60)
print("🔄 Loading AI models...")

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
client = QdrantClient("http://localhost:6333")

# Ensure chat_logs collection exists
try:
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    if "chat_logs" not in collection_names:
        client.create_collection(
            collection_name="chat_logs",
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE
            )
        )
        print("✅ Created 'chat_logs' collection")
except Exception as e:
    print(f"⚠️  Collection check: {e}")

llm = OllamaLLM(
    model="llama3.2:3b",
    temperature=0.7
)

print("✅ Models loaded successfully!")
print("="*60 + "\n")

# Thread lock for safe logging
log_lock = threading.Lock()
# AUTHENTICATION HELPER FUNCTIONS
def create_token(username):
    """Create JWT token with 24-hour expiration"""
    payload = {
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return username if valid"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['username']
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def require_auth(f):
    """Decorator to protect routes with authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        username = verify_token(token)
        
        if not username:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Pass username to the route function
        return f(username=username, *args, **kwargs)
    
    return decorated_function
# PUBLIC ROUTES (No Authentication Required)

@app.route('/')
def home():
    """Serve chatbot homepage"""
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS/JS/HTML)"""
    return send_from_directory('../frontend', path)

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    Handle chat requests (PUBLIC - No login required)
    Uses same logic as your original code
    """
    try:
        # Get request data
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4())[:8])
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        start_time = time.time()
        
        # Embed question
        query_vector = model.encode(question).tolist()
        
        # Search Qdrant
        results = client.query_points(
            collection_name="my_vectors",
            query=query_vector,
            limit=3
        )
        
        # Build context
        context = "\n\n".join([
            hit.payload['page_content']
            for hit in results.points
        ])
        
        # Generate answer using your existing prompt
        prompt = f"""Task
Primary Function: You are LushBot, a warm, knowledgeable, and enthusiastic Host.

IMPORTANT LINK RULES (MANDATORY):
1. Website: When mentioning the website, YOU MUST use this format: [www.lushgardenresort.in](https://www.lushgardenresort.in)
2. Location/Map: When asked about location/address, YOU MUST use this format: [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/CWrFFToUCVNhAE6LA)
3. Phone: +91-63694 24583
4. Email: [mailto:info@lushgardenresort.in](info@lushgardenresort.in)

CONTEXT (Use ONLY this information):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer using ONLY CONTEXT data.
2. HYPERLINK ENFORCEMENT:
   - NEVER write "www.lushgardenresort.in" as plain text. ALWAYS wrap it: [www.lushgardenresort.in](https://www.lushgardenresort.in)
   - NEVER write "Google Maps" as plain text. ALWAYS wrap it: [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/CWrFFToUCVNhAE6LA)
3. If the user asks for the location, provide the Google Maps link explicitly.
4. Be warm, professional, and engaging.
5. End with a dynamic follow-up question.

Answer as LushBot:"""

        answer = llm.invoke(prompt)
        elapsed = time.time() - start_time
        
        # Prepare sources
        sources = [
            {
                "content": hit.payload['page_content'][:200],
                "score": float(hit.score)
            }
            for hit in results.points
        ]
        
        # Save to Qdrant (thread-safe)
        with log_lock:
            timestamp = datetime.now().isoformat()
            log_id = str(uuid.uuid4())
            log_text = f"Question: {question}\nAnswer: {answer}\nTime: {timestamp}"
            log_vector = model.encode(log_text).tolist()
            
            client.upsert(
                collection_name="chat_logs",
                points=[
                    models.PointStruct(
                        id=log_id,
                        vector=log_vector,
                        payload={
                            "session_id": session_id,
                            "timestamp": timestamp,
                            "question": question,
                            "answer": answer.strip(),
                            "response_time": round(elapsed, 2),
                            "sources": sources,
                            "source_count": len(sources)
                        }
                    )
                ]
            )
        
        return jsonify({
            'answer': answer.strip(),
            'session_id': session_id,
            'timestamp': timestamp,
            'response_time': round(elapsed, 2),
            'sources': sources
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint (PUBLIC)"""
    return jsonify({
        'status': 'ok',
        'message': 'LushBot API running',
        'qdrant': 'connected',
        'ollama': 'connected'
    })

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint - Returns JWT token"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Hash the provided password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials
        if username in USERS and USERS[username] == hashed_password:
            token = create_token(username)
            return jsonify({
                'success': True,
                'token': token,
                'username': username,
                'message': 'Login successful'
            })
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/verify', methods=['GET'])
def verify():
    """Verify JWT token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    username = verify_token(token)
    
    if username:
        return jsonify({
            'success': True,
            'username': username,
            'message': 'Token valid'
        })
    else:
        return jsonify({'error': 'Invalid or expired token'}), 401

# ============================================
# PROTECTED ROUTES (Authentication Required)
# ============================================

@app.route('/api/logs', methods=['GET'])
@require_auth
def get_logs(username):
    """
    Get recent chat logs (PROTECTED - Requires login)
    Sorted by newest first
    """
    try:
        # Fetch logs from Qdrant
        results = client.scroll(
            collection_name="chat_logs",
            limit=100,  # Increase if you have more logs
            with_payload=True,
            with_vectors=False
        )
        
        logs = results[0]
        payloads = [log.payload for log in logs]
        
        # ✅ SORT BY TIMESTAMP (DESCENDING: Newest → Oldest)
        sorted_logs = sorted(
            payloads, 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        return jsonify({
            'success': True,
            'total': len(sorted_logs),
            'logs': sorted_logs,
            'accessed_by': username  # Track who accessed the logs
        })
        
    except Exception as e:
        print(f"❌ Error fetching logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# ADMIN ROUTES (Optional - Add more features)
# ============================================

@app.route('/api/logs/delete/<log_id>', methods=['DELETE'])
@require_auth
def delete_log(username, log_id):
    """Delete a specific log (PROTECTED)"""
    try:
        client.delete(
            collection_name="chat_logs",
            points_selector=models.PointIdsList(points=[log_id])
        )
        return jsonify({
            'success': True,
            'message': f'Log {log_id} deleted by {username}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats(username):
    """Get statistics about chat logs (PROTECTED)"""
    try:
        results = client.scroll(
            collection_name="chat_logs",
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        logs = [log.payload for log in results[0]]
        
        # Calculate statistics
        total_logs = len(logs)
        avg_response_time = sum(log.get('response_time', 0) for log in logs) / total_logs if total_logs > 0 else 0
        
        # Count today's logs
        today = datetime.now().date().isoformat()
        today_logs = sum(1 for log in logs if log.get('timestamp', '').startswith(today))
        
        return jsonify({
            'success': True,
            'total_logs': total_logs,
            'today_logs': today_logs,
            'avg_response_time': round(avg_response_time, 2),
            'accessed_by': username
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================
# START SERVER
# ============================================

if __name__ == '__main__':
    print("="*60)
    print("🚀 LUSHBOT SERVER - READY")
    print("="*60)
    print("\n📍 PUBLIC ROUTES:")
    print("   Chatbot:  http://localhost:5000")
    print("   API:      http://localhost:5000/api/ask")
    print("   Health:   http://localhost:5000/api/health")
    print("\n🔐 ADMIN ROUTES:")
    print("   Login:    http://localhost:5000/login.html")
    print("   Logs:     http://localhost:5000/logs.html")
    print("\n🔑 LOGIN CREDENTIALS:")
    print("   Username: admin")
    print("   Password: lushbot2026")
    print("="*60 + "\n")
    print("💡 Users can chat without login!")
    print("💡 Admins need login to view logs!")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
