import os
import json
import asyncio
import numpy as np
import faiss
import logging
import pickle
from datetime import datetime
from typing import List, Dict, Any

from llm_client import LLMClient

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, dimension: int = None, storage_dir: str = None):
        self.llm_client = LLMClient()
        test_embedding = self.llm_client.get_embedding("test")
        if not isinstance(test_embedding, (list, np.ndarray)):
            raise ValueError("Invalid embedding returned from LLM for dimension check.")

        self.dimension = dimension or len(test_embedding)
        self.storage_dir = storage_dir or os.path.join(os.path.expanduser("~"), ".ai_document_assistant")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = {}
        self.doc_count = 0

        self._load_index()

    def add_document(self, file_path: str, content: str, metadata: Dict[str, Any]) -> bool:
        try:
            embedding = self.llm_client.get_embedding(content)
            if not isinstance(embedding, (list, np.ndarray)):
                raise ValueError("Invalid embedding type")

            vector = self._prepare_vector(embedding)
            vector = np.array([vector], dtype=np.float32)
            faiss.normalize_L2(vector)

            self.index.add(vector)

            doc_id = self.doc_count
            self.documents[doc_id] = {
                "file_path": file_path,
                "metadata": metadata,
                "snippet": content[:1000],
                "timestamp": datetime.now().isoformat()
            }

            self.doc_count += 1
            if self.doc_count % 50 == 0:
                self._save_index()

            return True
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, self.llm_client.get_embedding, query)
            if not isinstance(embedding, (list, np.ndarray)):
                raise ValueError("Invalid embedding type")

            query_vector = self._prepare_vector(embedding)
            query_vector = np.array([query_vector], dtype=np.float32)
            faiss.normalize_L2(query_vector)

            if self.index.ntotal == 0:
                return []

            distances, indices = self.index.search(query_vector, min(limit * 2, self.index.ntotal))
            return self._format_results(indices[0], distances[0], limit)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    

    def reset(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = {}
        self.doc_count = 0

        for fname in ["index.faiss", "documents.pickle"]:
            fpath = os.path.join(self.storage_dir, fname)
            if os.path.exists(fpath):
                os.remove(fpath)

    def _save_index(self):
        try:
            faiss.write_index(self.index, os.path.join(self.storage_dir, "index.faiss"))
            with open(os.path.join(self.storage_dir, "documents.pickle"), "wb") as f:
                pickle.dump({"documents": self.documents, "doc_count": self.doc_count}, f)
        except Exception as e:
            logger.error(f"Saving vector store failed: {e}")

    def _load_index(self):
        try:
            index_path = os.path.join(self.storage_dir, "index.faiss")
            docs_path = os.path.join(self.storage_dir, "documents.pickle")
            if os.path.exists(index_path) and os.path.exists(docs_path):
                self.index = faiss.read_index(index_path)
                with open(docs_path, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.doc_count = data["doc_count"]
        except Exception as e:
            logger.error(f"Loading vector store failed: {e}")

    def _prepare_vector(self, embedding: List[float]) -> np.ndarray:
        embedding = np.array(embedding, dtype=np.float32)
        if len(embedding) > self.dimension:
            return embedding[:self.dimension]
        elif len(embedding) < self.dimension:
            return np.pad(embedding, (0, self.dimension - len(embedding)))
        return embedding

    def _format_results(self, indices, distances, limit):
        results = []
        seen = set()
        for i, idx in enumerate(indices):
            if idx < 0 or idx >= self.doc_count:
                continue
            doc = self.documents.get(int(idx))
            if not doc:
                continue
            path = doc["file_path"]
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            results.append({
                "file_path": path,
                "score": float(1.0 / (1.0 + distances[i])),
                "snippet": doc["snippet"],
                "metadata": doc["metadata"]
            })
            if len(results) >= limit:
                break
        return results
    
