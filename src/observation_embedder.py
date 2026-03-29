from typing import List

from sentence_transformers import SentenceTransformer


class EmbedderBase:
    def __init__(self):
        self.dim = None

    def embed(self, inputs: List[str]) -> List[List[float]]:
        if not inputs:
            return []
        return self._embed(inputs)

    def _embed(self, inputs: List[str]) -> List[List[float]]:
        raise NotImplementedError


class SentenceTransformerTextEmbedder(EmbedderBase):
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        super().__init__()
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dim = 768

    def _embed(self, inputs: List[str]) -> List[List[float]]:
        return self.model.encode(inputs).tolist()
