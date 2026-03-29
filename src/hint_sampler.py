import os
import random
from typing import Iterable, List, Optional, Set


DEFAULT_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself",
    "yourselves",
}


class HintSampler:
    def __init__(
        self,
        wordlist_path: str,
        stop_words: Optional[Iterable[str]] = None,
        seed: int = 42,
    ):
        if not os.path.exists(wordlist_path):
            raise FileNotFoundError(wordlist_path)
        self.wordlist_path = wordlist_path
        self.stop_words = set(stop_words) if stop_words is not None else DEFAULT_STOP_WORDS
        self.rng = random.Random(seed)
        self.words = self._load_words()

    def _load_words(self) -> List[str]:
        with open(self.wordlist_path, "r") as file:
            raw_words = [w.strip().lower() for w in file if len(w.strip()) > 0]
        filtered = [w for w in raw_words if w.isalpha() and w not in self.stop_words]
        if not filtered:
            raise ValueError("word list is empty after filtering stop words")
        return filtered

    def sample(self, count: int) -> List[str]:
        if count <= 0:
            raise ValueError("hint count must be positive")
        if count <= len(self.words):
            return self.rng.sample(self.words, count)
        return [self.rng.choice(self.words) for _ in range(count)]
