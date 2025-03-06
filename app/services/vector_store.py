from typing import List

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.services.chunking import ArticleChunk

openai_client = OpenAI()
qdrant_db_client = QdrantClient(url="http://localhost:6333")


def vectorize_text(text: str) -> List[float]:
  response = openai_client.embeddings.create(
      input=text,
      model="text-embedding-3-small"
  )
  return response.data[0].embedding


def embed_chunks(chunks: List[ArticleChunk], collection_name: str,
    category: str, id: str) -> None:
  points = []

  for article in chunks:
    article_number = article.number

    for clause in article.clauses:
      clause_content = clause.content
      clause_number = clause.number

      combined_text = f"Article {article_number}, Clause {clause_number}: {clause_content}"
      clause_vector = vectorize_text(combined_text)
      points.append(
          PointStruct(
              id=id,
              vector=clause_vector,
              payload={
                "category": category,
                "article_number": article_number,
                "clause_number": clause_number,
                "clause_content": clause_content
              }
          )
      )

      ensure_qdrant_collection(collection_name)
      upload_points_to_qdrant(collection_name, points)


def ensure_qdrant_collection(collection_name: str) -> None:
  collections = qdrant_db_client.get_collections()

  existing_collections = {
    col["name"] if isinstance(col, dict) else getattr(col, "name", None) for col
    in collections.collections}
  if collection_name not in existing_collections:
    create_qdrant_collection(collection_name)


def create_qdrant_collection(collection_name: str):
  return qdrant_db_client.create_collection(
      collection_name=collection_name,
      vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
  )


def upload_points_to_qdrant(collection_name, points):
  qdrant_db_client.upsert(collection_name=collection_name, points=points)

