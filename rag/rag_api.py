from rag.chroma import ChromaStore
from rag.indexer import Indexer
from rag.retriever import Retriever


class RAGAPI:
    """
    THE Public interface for the RAG module.

    Usage:
        rag = RAGAPI()
        rag.add_raw("quests", "q_001", "Eat Food: You are hungry.", {"source": "wiki"})
        results = rag.query("how do I stop being hungry?")
    """

    def __init__(self, persist_dir: str = "../data/chroma_db"):
        self.store = ChromaStore(persist_dir=persist_dir)
        self.indexer = Indexer(self.store)
        self.retriever = Retriever(self.store)

    def add_raw(self, collection: str, id: str, text: str, metadata: dict = {}):
        self.indexer.add_raw(collection, id, text, metadata)

    def add_bulk(self, collection: str, docs: list[dict]):
        self.indexer.add_bulk(collection, docs)

    def query(self, query: str, n_per_collection: int = 3) -> list[dict]:
        """
        Query across all collections.
        Returns a ranked list of:
            {"text": str, "metadata": dict, "score": float, "collection": str}
        """
        return self.retriever.query(query, n_per_collection)