from fastembed import SparseTextEmbedding

class FastEmbedSparseWrapper:
    def __init__(self, model_name: str):
        self.model = SparseTextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list:
        return list(self.model.embed(texts))

def get_sparse_embedding_client():
    return FastEmbedSparseWrapper("prithivida/Splade_PP_en_v1")