from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_ollama import OllamaLLM


print("🔄 Loading RAG database...")


# Initialize embeddings and Qdrant
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
client = QdrantClient(url="http://localhost:6333")


qdrant = QdrantVectorStore(
    client=client,
    collection_name="my_vectors",
    embedding=embeddings
)


print("✅ Database loaded!")


# Initialize Ollama with Llama 3B
llm = OllamaLLM(
    model="llama3.2:3b",  # or "llama3.2:1b" or "llama3.1:8b"
    temperature=0.7,
    base_url="http://localhost:11434"
)


print("🤖 Ollama LLM (Llama 3B) ready!\n")



def generate_answer(question, context):
    """Generate answer using Ollama with LushBot persona"""
    prompt = f"""Task
    Primary Function: You are LushBot, a warm, knowledgeable, and enthusiastic Host dedicated to assisting guests with inquiries about Lush Garden Resorts.

    IMPORTANT: You MUST answer based ONLY on the information provided in the CONTEXT section below. Do not use any external knowledge.

    CONTEXT (Information from our database):
    {context}

    USER QUESTION: {question}

    INSTRUCTIONS:
    1. First, carefully read the CONTEXT above
    2. Answer the user's question using ONLY information from the CONTEXT
    3. If the CONTEXT doesn't contain the answer, say "I don't have that information in our database."
    4. Follow the LushBot persona: be warm, professional, and engaging
    5. End with a dynamic follow-up question
    6. Do NOT mention "context" or "database" in your answer
    7. Structure your response with headings and line gaps for readability
    8. Avoid markdown symbols like ** or *

    Answer as LushBot:"""
    
    response = llm.invoke(prompt)
    return response



# Questions
questions = [
    "What is the official website for your resort?",
    "What are the pool hours?",
    "How can I book a villa?"
]



for question in questions:
    print(f"❓ Question: {question}\n")
    
    # Search similar documents
    docs = qdrant.similarity_search(question, k=2)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Generate answer
    answer = generate_answer(question, context)
    
    print(f"🤖 Answer: {answer}\n")
    print(f"📚 Sources:")
    for i, doc in enumerate(docs, 1):
        print(f"   {i}. {doc.page_content[:150]}...")
    print("\n" + "="*80 + "\n")
