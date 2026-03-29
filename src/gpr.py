import json
import logging
import random
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.decomposition import PCA
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct, Matern, RBF, WhiteKernel
from sklearn.preprocessing import StandardScaler

from .keyword_list import KeywordList
from .observation_embedder import SentenceTransformerTextEmbedder


@dataclass
class GPRConfig:
    warmup: int = 100
    window_size: Optional[int] = 2
    reduce_feature_dim: Optional[int] = None
    kernel: str = "dotproduct"
    random_state: int = 0


class GPRHintSelector:
    def __init__(self, config: Optional[GPRConfig] = None):
        self.config = config or GPRConfig()
        self.rng = random.Random(self.config.random_state)
        self.kernel = self._build_kernel(self.config.kernel)
        self.embedder = SentenceTransformerTextEmbedder()

    def _build_kernel(self, name: str):
        if name == "dotproduct":
            return DotProduct() + WhiteKernel()
        if name == "matern_nu2.5":
            return Matern(nu=2.5) + WhiteKernel()
        if name == "matern_nu1.5":
            return Matern(nu=1.5) + WhiteKernel()
        if name == "rbf":
            return RBF() + WhiteKernel()
        raise ValueError(f"Unknown kernel {name}")

    def _load_entries(self, record_jsonl_path: str) -> List[dict]:
        try:
            with open(record_jsonl_path, "r") as file:
                lines = [l.strip() for l in file if l.strip()]
        except FileNotFoundError:
            return []
        entries = []
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(entry)
        return entries

    def _extract_entry(self, entry: dict):
        hints = entry.get("hints")
        fb_emb = entry.get("fb_emb") or entry.get("feedback_embedding")
        if not hints or fb_emb is None:
            return None
        if not isinstance(fb_emb, list) or any(v is None for v in fb_emb):
            return None
        keyword_list = KeywordList(hints).keyword_list
        if not keyword_list:
            return None
        return {"id": entry.get("id"), "hints": keyword_list, "fb_emb": fb_emb}

    def _build_observation_vectors(
        self,
        observations: Sequence[str],
        entry_observations: Sequence[Sequence[str]],
        predicting_observations: Sequence[Sequence[str]],
        training_y: Sequence[List[float]],
    ) -> Tuple[List[np.ndarray], List[List[float]], List[np.ndarray]]:
        obs_vectors = self.embedder.embed(list(observations))
        obs_index = {obs: i for i, obs in enumerate(observations)}

        training_X = [
            np.sum(np.stack([obs_vectors[obs_index[o]] for o in obs_list]), axis=0)
            for obs_list in entry_observations
        ]
        predicting_X = [
            np.sum(np.stack([obs_vectors[obs_index[o]] for o in obs_list]), axis=0)
            for obs_list in predicting_observations
        ]

        if self.config.reduce_feature_dim is None:
            return training_X, training_y, predicting_X

        normalized = StandardScaler().fit_transform(training_X + predicting_X)
        reduced = PCA(n_components=self.config.reduce_feature_dim, random_state=self.config.random_state).fit_transform(normalized)
        reduced_training = [v for v in reduced[:len(training_X)]]
        reduced_predicting = [v for v in reduced[len(training_X):]]
        return reduced_training, training_y, reduced_predicting

    def _predict(self, training_X, training_y, predicting_X):
        gpr = GaussianProcessRegressor(kernel=self.kernel, random_state=self.config.random_state)
        gpr.fit(training_X, training_y)
        return gpr.predict(predicting_X)

    def choose_best(
        self,
        record_jsonl_path: str,
        candidates: Sequence[Sequence[str]],
        observation_fn: Callable[[str], str],
    ) -> int:
        entries = [self._extract_entry(e) for e in self._load_entries(record_jsonl_path)]
        entries = [e for e in entries if e is not None]

        if len(entries) < self.config.warmup:
            return self.rng.randrange(len(candidates))

        if self.config.window_size is not None and self.config.window_size > 0:
            entries = entries[-self.config.window_size :]

        entry_observations = [[observation_fn(h) for h in e["hints"]] for e in entries]
        entry_observations = [[o for o in obs_list if o] for obs_list in entry_observations]
        predicting_observations = [[observation_fn(h) for h in c] for c in candidates]
        predicting_observations = [[o for o in obs_list if o] for obs_list in predicting_observations]
        filtered_entries = []
        filtered_entry_obs = []
        for entry, obs_list in zip(entries, entry_observations):
            if obs_list:
                filtered_entries.append(entry)
                filtered_entry_obs.append(obs_list)
        entries = filtered_entries
        entry_observations = filtered_entry_obs

        observations = sorted({o for obs_list in entry_observations + predicting_observations for o in obs_list if o})
        if not observations:
            return self.rng.randrange(len(candidates))

        training_y = [e["fb_emb"] for e in entries]
        training_X, training_y, predicting_X = self._build_observation_vectors(
            observations,
            entry_observations,
            predicting_observations,
            training_y,
        )
        if not training_X or not predicting_X:
            return self.rng.randrange(len(candidates))

        predicted_y = self._predict(training_X, training_y, predicting_X)
        quality = [float(np.mean(y)) for y in predicted_y]
        best_idx = int(np.argsort(quality)[0])
        logging.info("GPR select hints: idx=%s quality=%s", best_idx, quality)
        return best_idx
