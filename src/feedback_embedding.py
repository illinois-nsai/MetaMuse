import time
from typing import List

from simulators.base import Simulator


class FeedbackEmbedding:
    def __init__(self, simulators: List[Simulator]):
        if not simulators:
            raise ValueError("simulators list cannot be empty")
        self.simulators = simulators
        self.latency = 0.0

    @property
    def dimension(self):
        return len(self.simulators)

    def _normalize(self, raw: List[float]):
        return raw

    def embed(self, code: str) -> List[float]:
        start = time.time()
        fb_emb = [sim.simulate(code=code, code_id="fb_emb") for sim in self.simulators]
        self.latency += time.time() - start
        return self._normalize(fb_emb)

    def to_dict(self):
        return {
            "simulators": [sim.to_dict() for sim in self.simulators],
            "latency": self.latency,
        }
