from flask import Blueprint, request, jsonify
from model import vectorstore, llm, client, embeddings, log_lock
from qdrant_client import models
import time
import uuid
from datetime import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Public Chat API Ready',
        'langchain': 'connected',
        'qdrant': 'connected'
    })

@api_bp.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4())[:8])
        
        if not question:
            return jsonify({'error': 'Question required'}), 400
        
        start_time = time.time()
        
        # 🔥 LANGCHAIN RAG PIPELINE
        docs = vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # ✅ FIXED: Single prompt assignment
        prompt = f"""Task: You are LushBot, a warm, knowledgeable resort host.

IMPORTANT LINK RULES (MANDATORY):
1. Website: [www.lushgardenresort.in](https://www.lushgardenresort.in)
2. Location: [View on Google Maps](https://maps.app.goo.gl/CWrFFToUCVNhAE7)
3. Phone: +91-63694 24583
4. Email: mailto:info@lushgardenresort.in

CONTEXT (Use ONLY this information):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer using ONLY CONTEXT data
2. Be warm, professional, engaging
3. End with a follow-up question

Answer:"""

        answer = llm.invoke(prompt)
        elapsed = round(time.time() - start_time, 2)
        
        # ✅ FIXED: Use embeddings + log_lock + PointStruct
        with log_lock:
            log_vector = embeddings.embed_query(f"{question} {answer}")
            client.upsert(
                collection_name="chat_logs",
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=log_vector,
                        payload={
                            'session_id': session_id,
                            'timestamp': datetime.now().isoformat(),
                            'question': question,
                            'answer': answer,
                            'response_time': elapsed,
                            'sources': len(docs)
                        }
                    )
                ]
            )
        
        return jsonify({
            'answer': answer.strip(),
            'session_id': session_id,
            'response_time': elapsed,
            'sources': len(docs)
        })
    except Exception as e:
        import traceback
        print(f"❌ ERROR in /ask: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
