from .chroma import ChromaStore


class Indexer:
    """
    Loads raw text into ChromaStore.
    Higher-level functionality will be added later.
    """

    def __init__(self, store: ChromaStore):
        self.store = store

    def add_raw(self, collection: str, id: str, text: str, metadata: dict = {}):
        """
        Adds a single raw text entry to a collection.

        collection: "quests" or "lore"
        id:         unique identifier e.g. "q_001"
        text:       raw text content
        metadata:   optional tags e.g. {"source": "wiki"}
        """
        self.store.add(collection, [{
            "id": id,
            "text": text,
            "metadata": metadata
        }])

    def add_bulk(self, collection: str, docs: list[dict]):
        self.store.add(collection, docs)