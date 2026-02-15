from qdrant_client import QdrantClient

client = QdrantClient("http://localhost:6333")
results = client.scroll(collection_name="my_vectors", limit=10)

print(" First 10 entries in your CSV:\n")
for i, point in enumerate(results[0], 1):
    content = point.payload.get('page_content', 'N/A')
    print(f"{i}. {content[:250]}\n")
