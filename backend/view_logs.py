from qdrant_client import QdrantClient
from datetime import datetime

client = QdrantClient("http://localhost:6333")

print(" Chat Logs from Qdrant Database\n")

# Get all logs
results = client.scroll(
    collection_name="chat_logs",
    limit=100,
    with_payload=True,
    with_vectors=False
)

logs = results[0]  # First element is the list of points

if not logs:
    print("No logs found.")
else:
     sorted_logs = sorted(
        logs,
        key=lambda x: x.payload.get('timestamp', ''),
        reverse=True  # Newest first
    )
     print(f"Total Logs: {len(logs)}\n")
     print("="*80)
    
for i, log in enumerate(sorted_logs, 1):
        payload = log.payload
        print(f"\n📝 Log #{i}")
        print(f"Session ID: {payload.get('session_id', 'N/A')}")
        print(f"Timestamp: {payload.get('timestamp', 'N/A')}")
        print(f"Question: {payload.get('question', 'N/A')}")
        print(f"Answer: {payload.get('answer', 'N/A')[:200]}...")
        print(f"Response Time: {payload.get('response_time', 'N/A')}s")
        print(f"Sources Used: {payload.get('source_count', 0)}")
        print("="*80)
