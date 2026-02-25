from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

print("Loading CSV...")
loader = CSVLoader("dataset_ai.csv")
docs = loader.load()

print("Splitting...")
texts = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)

print("Embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

print("Creating collection...")
client = QdrantClient("http://localhost:6333")
client.recreate_collection("my_vectors", vectors_config=VectorParams(size=384, distance=Distance.COSINE))

print("Ingestion...")
QdrantVectorStore.from_documents(texts, embeddings, url="http://localhost:6333", collection_name="my_vectors")
print(" RAG DATABASE READY!")
