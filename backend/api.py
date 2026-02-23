from flask import Blueprint, request,jsonify
from model import vectorstore, llm
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
    """Public chat endpoint - LangChain RAG from CSV"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4())[:8])
        
        if not question:
            return jsonify({'error': 'Question required'}), 400
        
        start_time = time.time()
        
        # 🔥 LANGCHAIN RAG PIPELINE (Your teacher's method!)
        docs = vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Prompt with LINKS (clickable in frontend)
        prompt =    prompt = f"""Task
Primary Function: You are LushBot, a warm, knowledgeable, and enthusiastic Host.


IMPORTANT LINK RULES (MANDATORY):
1. Website: When mentioning the website, YOU MUST use this format: www.lushgardenresort.in
2. Location/Map: When asked about location/address, YOU MUST use this format: Lush Garden Resort - Google Maps
3. Phone: +91-63694 24583
4. Email: mailto:info@lushgardenresort.in


CONTEXT (Use ONLY this information):
{context}


USER QUESTION: {question}


INSTRUCTIONS:
1. Answer using ONLY CONTEXT data.
2. HYPERLINK ENFORCEMENT:
   - NEVER write "www.lushgardenresort.in" as plain text. ALWAYS wrap it: www.lushgardenresort.in
   - NEVER write "Google Maps" as plain text. ALWAYS wrap it: Lush Garden Resort - Google Maps
3. If the user asks for the location, provide the Google Maps link explicitly.
4. Be warm, professional, and engaging.
5. End with a dynamic follow-up question.


Answer as LushBot:"""

        answer = llm.invoke(prompt)
        elapsed = round(time.time() - start_time, 2)
        
        # Save to chat_logs collection
        from models import client, model, log_lock
        with log_lock:
            log_vector = model.encode(f"{question} {answer}").tolist()
            client.upsert("chat_logs", [{
                'id': str(uuid.uuid4()),
                'vector': log_vector,
                'payload': {
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat(),
                    'question': question,
                    'answer': answer,
                    'response_time': elapsed
                }
            }])
        
        return jsonify({
            'answer': answer.strip(),
            'session_id': session_id,
            'response_time': elapsed,
            'sources': len(docs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
