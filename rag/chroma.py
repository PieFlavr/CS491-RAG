import chromadb
from chromadb.utils import embedding_functions

COLLECTIONS = ["quests", "lore"]

class ChromaStore:
    def __init__(self, persist_dir: str = "../data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)

        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collections = {
            name: self.client.get_or_create_collection(
                name=name,
                embedding_function = self.embed_fn, # type: ignore
                # the type checking is just overly strict i guess? works regardless
                metadata={"hnsw:space": "cosine"},
            )
            for name in COLLECTIONS
        }

    def add(self, collection: str, docs: list[dict]):
        if collection not in self.collections:
            raise ValueError(f"Unknown collection '{collection}'. Choose from: {COLLECTIONS}")

        col = self.collections[collection]
        col.upsert(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[d.get("metadata", {}) for d in docs],
        )

    def query(self, collection: str, text: str, n: int = 5, filters: dict = None) -> list[dict]: # type: ignore
        if collection not in self.collections:
            raise ValueError(f"Unknown collection '{collection}'. Choose from: {COLLECTIONS}")

        col = self.collections[collection]
        kwargs = {
            "query_texts": [text],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"]
        }
        if filters:
            kwargs["where"] = filters

        raw = col.query(**kwargs)

        return [
            {
                "text": raw["documents"][0][i], # type: ignore
                "metadata": raw["metadatas"][0][i], # type: ignore
                "score": 1 - raw["distances"][0][i], # type: ignore
            }
            for i in range(len(raw["documents"][0])) # type: ignore
        ]

    def delete(self, collection: str, ids: list[str]):
        self.collections[collection].delete(ids=ids)

    def count(self, collection: str) -> int:
        return self.collections[collection].count()