from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient("http://localhost:6333")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Search for similar questions in logs
search_query = input("🔍 Search logs for: ")

query_vector = model.encode(search_query).tolist()

# ✅ CORRECT METHOD: query_points (not search)
results = client.query_points(
    collection_name="chat_logs",
    query=query_vector,
    limit=5
)

print(f"\n📊 Top {len(results.points)} matching logs:\n")

for i, hit in enumerate(results.points, 1):
    payload = hit.payload
    print(f"\n{i}. [Match: {hit.score:.0%}]")
    print(f"   Time: {payload.get('timestamp', 'N/A')}")
    print(f"   Q: {payload.get('question', 'N/A')}")
    print(f"   A: {payload.get('answer', 'N/A')[:150]}...")
    print(f"   Response: {payload.get('response_time', 'N/A')}s")
    print("-"*80)
