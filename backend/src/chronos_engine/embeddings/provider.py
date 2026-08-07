import math
import re
from typing import List
from chronos_engine.core.interfaces import BaseEmbeddingProvider


class DefaultEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic lightweight semantic embedding generator for Chronos Engine.
    Uses 128-dimensional hashed n-gram projection with L2 normalization to compute
    cosine similarities between text memories.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    async def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        words = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dimension

        # Generate unigram and bigram features hashed into target dimension
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(words[i] + "_" + words[i + 1])

        for token in tokens:
            h = hash(token)
            idx = abs(h) % self.dimension
            sign = 1.0 if h > 0 else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return float(dot)
