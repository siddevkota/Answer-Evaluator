from typing import Dict, Any, List, Tuple
import numpy as np
from .llm import embed_texts

class SimpleVectorStore:
    def __init__(self) -> None:
        self.vectors: List[np.ndarray] = []
        self.metadatas: List[Dict[str, Any]] = []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not texts:
            return
        embs = embed_texts(texts)
        for e, m in zip(embs, metadatas):
            self.vectors.append(np.array(e, dtype=np.float32))
            self.metadatas.append(m)

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if not self.vectors:
            return []
        q_emb = np.array(embed_texts([query])[0], dtype=np.float32)
        sims = []
        for idx, v in enumerate(self.vectors):
            sim = float(np.dot(q_emb, v) / (np.linalg.norm(q_emb) * np.linalg.norm(v)))
            sims.append((sim, idx))
        sims.sort(reverse=True, key=lambda x: x[0])
        results: List[Dict[str, Any]] = []
        for score, idx in sims[:k]:
            meta = dict(self.metadatas[idx])
            meta["score"] = score
            results.append(meta)
        return results

# Global stores for simplicity
syllabus_store = SimpleVectorStore()
textbook_store = SimpleVectorStore()
