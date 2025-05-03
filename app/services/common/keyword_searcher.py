from contextlib import asynccontextmanager
from fastembed import SparseTextEmbedding

class FastEmbedSparseWrapper:
    def __init__(self, model_name: str):
        self.model = SparseTextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list:
        return list(self.model.embed(texts))

@asynccontextmanager
async def get_sparse_embedding_async_client():
    wrapper = FastEmbedSparseWrapper("prithivida/Splade_PP_en_v1")
    yield wrapper
