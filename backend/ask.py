from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM
import time
import logging
from datetime import datetime
import uuid

#  SETUP FILE LOGGING (backup)
logging.basicConfig(
    filename='chat_history.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d-%m-%Y'' %H:%M:%S'
)

print(" Loading models...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
client = QdrantClient("http://localhost:6333")

llm = OllamaLLM(
    model="llama3.2:3b",
    temperature=0.7
)

print(" Ready! Ask me anything!\n")

# Session ID for tracking
session_id = str(uuid.uuid4())[:8]
logging.info(f"SESSION STARTED - ID: {session_id}")

while True:
    question = input("❓ You: ")
    if question.lower() == 'quit':
        print("👋 Goodbye!")
        logging.info(f"SESSION ENDED - ID: {session_id}")
        break
    
    start_time = time.time()
    
    # Embed question
    query_vector = model.encode(question).tolist()
    
    # Search Qdrant
    results = client.query_points(
        collection_name="my_vectors",
        query=query_vector,
        limit=3
    )
    
    context = "\n\n".join([
        hit.payload['page_content']
        for hit in results.points
    ])
    
    # Generate answer
    prompt = f"""Task
Primary Function: You are LushBot, a warm, knowledgeable, and enthusiastic Host.

IMPORTANT LINK RULES (MANDATORY):
1. Website → [www.lushgardenresort.in](https://www.lushgardenresort.in)
2. Location → [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/your-actual-link)
3. Phone → +91-XXXXXXXXXX
4. Email → info@lushgardenresort.in

CONTEXT (Use ONLY this information):
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer using ONLY CONTEXT data.
2. If the user asks about the website or more info, use exactly: [www.lushgardenresort.in](https://www.lushgardenresort.in)
3. If the user asks about location or address, use exactly: [Lush Garden Resort - Google Maps](https://maps.app.goo.gl/CWrFFToUCVNhAE6LA)
4. Use standard Markdown: [Link Text](URL) - DO NOT put stars (**) around the brackets.
5. Be warm, professional, and engaging.
6. End with a dynamic follow-up question.

Answer as LushBot:"""
    
    answer = llm.invoke(prompt)
    elapsed = time.time() - start_time
    
    # Display answer
    print(f"\n🤖 Bot: {answer}\n")
    print(" Sources:")
    for i, hit in enumerate(results.points, 1):
        print(f"   {i}. [Score: {hit.score:.0%}] {hit.payload['page_content'][:100]}...")
    print(f"⏱️  {elapsed:.2f}s\n")
    
    #  SAVE TO QDRANT DATABASE
    timestamp = datetime.now().isoformat()
    log_id = str(uuid.uuid4())
    
    # Create searchable log entry
    log_text = f"Question: {question}\nAnswer: {answer}\nTime: {timestamp}"
    log_vector = model.encode(log_text).tolist()
    
    # Prepare sources
    sources = [
        {
            "content": hit.payload['page_content'][:200],
            "score": float(hit.score)
        }
        for hit in results.points
    ]
    
    try:
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
        print("💾 Logged to Qdrant database")
    except Exception as e:
        print(f"⚠️  Qdrant log failed: {e}")
    
    # ✅ BACKUP TO FILE
    logging.info("="*80)
    logging.info(f"SESSION: {session_id}")
    logging.info(f"QUESTION: {question}")
    logging.info(f"ANSWER: {answer.strip()}")
    logging.info(f"TIME: {elapsed:.2f}s")
    logging.info("="*80)
    
    print("="*80 + "\n")
