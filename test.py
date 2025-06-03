import json
import tqdm
from qdrant_client import QdrantClient, models

dense_vector_name = "dense"
sparse_vector_name = "sparse"
dense_model_name = "sentence-transformers/all-MiniLM-L6-v2"
sparse_model_name = "prithivida/Splade_PP_en_v1"

def main():
    client = QdrantClient(url="http://localhost:6333")

    # 컬렉션이 없다면 생성
    if not client.collection_exists("startups"):
        client.create_collection(
            collection_name="startups",
            vectors_config={
                dense_vector_name: models.VectorParams(
                    size=client.get_embedding_size(dense_model_name),
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                sparse_vector_name: models.SparseVectorParams()
            },
        )

    # JSON 로딩
    payload_path = "D:/poscodx/finalPJ/startups_demo.json"
    documents = []
    metadata = []

    with open(payload_path, encoding="utf-8") as fd:
        for line in fd:
            obj = json.loads(line)
            description = obj["description"]
            dense_document = models.Document(text=description, model=dense_model_name)
            sparse_document = models.Document(text=description, model=sparse_model_name)
            documents.append({
                dense_vector_name: dense_document,
                sparse_vector_name: sparse_document
            })
            metadata.append(obj)

    # 업로드 (병렬 처리)
    client.upload_collection(
        collection_name="startups",
        vectors=tqdm.tqdm(documents),
        payload=metadata,
        parallel=4,  # ✅ 병렬 사용 시 반드시 __main__ 블록 안에서 실행
    )

# Windows 안전 실행 진입점
if __name__ == "__main__":
    main()
