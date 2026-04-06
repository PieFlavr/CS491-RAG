from rag.chroma import ChromaStore
from rag.rag_config import RetrieverConfig

class Retriever:
    """
    Queries ChromaStore across all collections and returns
    a ranked list of relevant results for a given query.
    """

    def __init__(self, store: ChromaStore, config = None):
        """_summary_
        Initializes the Retriever with a ChromaStore instance and an optional configuration.
        
        Args:
            store (ChromaStore): An instance of the ChromaStore class to query against.
            config (_type_, optional): Configuration settings for the Retriever. Defaults to None, which will load default settings from RetrieverConfig.
        """        
        self.store = store
        if config is None: 
            config = RetrieverConfig()
        self.config = config

    def query(self, query: str, n_per_collection: int | None = None, score_threshold: float | None = None) -> list[dict]:
        """_summary_
            Queries all collections in the ChromaStore for the given query and returns a ranked list of results that meet the score threshold.
        
        Args:
            query (str): The query string to search for in the ChromaStore.
            n_per_collection (int | None, optional): The number of results to retrieve from each collection. Defaults to None, using the value from RetrieverConfig configuration.
            score_threshold (float | None, optional): The minimum score for results to be included. Defaults to None, using the value from RetrieverConfig configuration. 

        Returns:
            list[dict]: A ranked list of relevant results across all collections.
        """        

        results = []

        if n_per_collection is None:
            n_per_collection = self.config.n_per_collection
        if score_threshold is None:
            score_threshold = self.config.score_threshold

        for collection in ["quests", "lore"]:
            try:
                hits = self.store.query(collection, query, n=n_per_collection)
                for hit in hits:
                    hit["collection"] = collection  # tag where it came from
                results.extend(hits)
            except Exception as e:
                print(f"[Retriever] Skipped '{collection}': {e}")

        results = [r for r in results if r["score"] >= score_threshold]
        results.sort(key=lambda r: r["score"], reverse=True)

        return results