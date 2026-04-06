from rag.chroma import ChromaStore
from rag.indexer import Indexer
from rag.retriever import Retriever
from rag.manifest import Manifest
from rag.loader import ingest_folder, preview_folder
from rag.rag_config import RAGConfig

class RAGAPI:
    """
    Public interface for the RAG module.

    Usage:
        rag = RAGAPI()
        rag.ingest("./data/rawHTML", "lore")
        results = rag.query("what is Ashenvale?")
    """

    def __init__(self, persist_dir: str = "./data/chroma_db", 
                 config: RAGConfig | None = None,
                 config_dir: str = "rag_config.json"):
        """
        Initializes the RAGAPI with a ChromaStore.

        Args:
            persist_dir (str, optional): The directory to persist the Chroma database. Defaults to "./data/chroma_db".
            config_dir (str, optional): The path to the configuration file. Defaults to "rag_config.json".
            config (RAGConfig | None, optional): The RAG configuration. Defaults to None.
        """       
        self.config = RAGConfig.load(config_dir) if config is None else config

        self.store    = ChromaStore(persist_dir=persist_dir, config=self.config.chroma)
        self.indexer  = Indexer(self.store)
        self.retriever = Retriever(self.store, config=self.config.retriever)
        self.manifest = Manifest(chroma_dir=persist_dir)

    def add_raw(self, collection: str, id: str, text: str, metadata: dict = {}):
        self.indexer.add_raw(collection, id, text, metadata)

    def add_bulk(self, collection: str, docs: list[dict]):
        self.indexer.add_bulk(collection, docs)

    def preview(self, folder: str, collection: str):
        """Preview what would be ingested from a folder without writing anything."""
        preview_folder(folder, collection)

    def ingest(self, folder: str, collection: str, force: bool = False):
        """
        Ingest a folder into a collection.
        Skips already ingested files unless force=True.
        """
        ingest_folder(folder, collection, self.indexer, self.manifest, force=force)

    def query(self, query: str, n_per_collection: int = 3) -> list[dict]:
        """
        Query across all collections.
        Returns a ranked list of:
            {"text": str, "metadata": dict, "score": float, "collection": str}
        """
        return self.retriever.query(query, n_per_collection)

    # region Manifest Management

    def show_manifest(self):
        """Prints everything currently recorded in the manifest."""
        data = self.manifest.all()
        if not data:
            print("Manifest is empty.")
            return
        print(f"{'File':<40} {'Collection':<12} Ingested At")
        print("-" * 70)
        for filename, info in data.items():
            print(f"{filename:<40} {info['collection']:<12} {info['ingested_at']}")

    def force_reingest(self, folder: str, collection: str):
        """Re-ingests all files in a folder regardless of manifest."""
        ingest_folder(folder, collection, self.indexer, self.manifest, force=True)

    def clear_manifest(self):
        """Clears the manifest so all files will be re-ingested on next run."""
        self.manifest.clear()
        print("Manifest cleared.")

    # endregion Manifest Management