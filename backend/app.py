from flask import Flask, request,jsonify, render_template, send_from_directory
from flask_cors import CORS
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM
from datetime import datetime
import uuid
import threading
import time
import os

app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend')
CORS(app)

# Initialize models (same as your ask.py)
print("🔄 Loading models...")
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
    print(f"⚠️ Note: Collection check skipped/failed: {e}")

llm = OllamaLLM(
    model="llama3.2:3b",  # Same as your ask.py
    temperature=0.7
)
print("✅ Models loaded! Server ready.")

# Thread lock for safe logging
log_lock = threading.Lock()

@app.route('/')
def home():
    """Serve frontend HTML"""
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve CSS/JS files"""
    return send_from_directory('../frontend', path)

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    Handle chat requests
    Uses same logic as your ask.py
    """
    try:
        # Get request data
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4())[:8])
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        start_time = time.time()
        
        # Embed question (same as ask.py)
        query_vector = model.encode(question).tolist()
        
        # Search Qdrant (same as ask.py)
        results = client.query_points(
            collection_name="my_vectors",
            query=query_vector,
            limit=3  # Same limit as your ask.py
        )
        
        # Build context (same as ask.py)
        context = "\n\n".join([
            hit.payload['page_content']
            for hit in results.points
        ])
        
        # Generate answer using same prompt from ask.py
        prompt = f"""Task
Primary Function: You are LushBot, a warm, knowledgeable, and enthusiastic Host.

IMPORTANT LINK RULES (MANDATORY):
1. Website → [www.lushgardenresort.in](https://www.lushgardenresort.in)
2. Location → [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/CWrFFToUCVNhAE6LA)
3. Phone → +91-XXXXXXXXXX
4. Email → info@lushgardenresort.in

CONTEXT (Use ONLY this information):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer using ONLY CONTEXT data.
2. If the user asks about the website or more info, use exactly: [www.lushgardenresort.in](https://www.lushgardenresort.in)
3. If the user asks about location or address, use exactly: [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/your-actual-link)
4. Use standard Markdown: [Link Text](URL) - DO NOT put stars (**) around the brackets.
5. Be warm, professional, and engaging.
6. End with a dynamic follow-up question.

Answer as LushBot:"""

        
        answer = llm.invoke(prompt)
        elapsed = time.time() - start_time
        
        # Prepare sources (same as ask.py)
        sources = [
            {
                "content": hit.payload['page_content'][:200],
                "score": float(hit.score)
            }
            for hit in results.points
        ]
        
        # Save to Qdrant (thread-safe, same as ask.py)
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
    """Health check"""
    return jsonify({
        'status': 'ok',
        'message': 'LushBot API running',
        'qdrant': 'connected',
        'ollama': 'connected'
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent chat logs (sorted by newest first)"""
    try:
        # Fetch logs (increase limit if needed, e.g., 50)
        results = client.scroll(
            collection_name="chat_logs",
            limit=50,  # Get more logs to sort properly
            with_payload=True,
            with_vectors=False
        )
        
        logs = results[0]
        payloads = [log.payload for log in logs]
        
        # ✅ SORT BY TIMESTAMP (DESCENDING: Newest -> Oldest)
        # Assuming 'timestamp' format is ISO 8601 (e.g., "2026-02-10T15:56:53...")
        sorted_logs = sorted(
            payloads, 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        return jsonify({
            'total': len(sorted_logs),
            'logs': sorted_logs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting LushBot Flask Server...")
    print("📍 Frontend: http://localhost:5000")
    print("📍 API: http://localhost:5000/api/ask")
    print("📍 Logs: http://localhost:5000/api/logs")
    print("\n✅ Ready! Open browser to http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
