from rag.chroma import ChromaStore

SCORE_THRESHOLD = 0.3  # results below this get dropped, we can replace this with something smarter later

class Retriever:
    """
    Queries ChromaStore across all collections and returns
    a ranked list of relevant results for a given query.
    """

    def __init__(self, store: ChromaStore):
        self.store = store

    def query(self, query: str, n_per_collection: int = 3) -> list[dict]:
        """
        Searches all collections and returns merged, ranked results.

        query:              the search text
        n_per_collection:   how many results to pull from each collection

        Returns a list of:
            {"text": str, "metadata": dict, "score": float, "collection": str}
        sorted by score, highest first.
        """
        results = []

        for collection in ["quests", "lore"]:
            try:
                hits = self.store.query(collection, query, n=n_per_collection)
                for hit in hits:
                    hit["collection"] = collection  # tag where it came from
                results.extend(hits)
            except Exception as e:
                print(f"[Retriever] Skipped '{collection}': {e}")

        results = [r for r in results if r["score"] >= SCORE_THRESHOLD]
        results.sort(key=lambda r: r["score"], reverse=True)

        return results