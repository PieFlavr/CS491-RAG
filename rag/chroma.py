import chromadb
from chromadb.utils import embedding_functions
from rag import rag_config
from rag.rag_config import ChromaConfig

COLLECTIONS = ["quests", "lore"]

class ChromaStore:
    def __init__(self, persist_dir: str = "../data/chroma_db", config_dir: str = "chroma_config.json", config: ChromaConfig | None = None):
        """_summary_
            Initializes the ChromaStore with a persistent ChromaDB client and sets up collections and embedding functions.

        Args:
            persist_dir (str, optional): The directory where the ChromaDB is persisted. Defaults to "../data/chroma_db".
            config_dir (str, optional): The path to the JSON configuration file. Defaults to "chroma_config.json".
            config (ChromaConfig, optional): The configuration settings for the ChromaStore. Defaults to None.
                                                If None, constructs a new ChromaConfig instance by loading from config_dir.
        """        
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
        if config is None:
            self.load_config(config_dir)
        else:
            self.config = config

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
    
    # region Configuration

    def load_config(self, path: str = "chroma_config.json"):
        """_summary_
        Loads configuration settings from a JSON file and applies them to the ChromaStore instance.

        Args:
            path (str, optional): The path to the JSON configuration file. Defaults to "chroma_config.json".
        """        
        config = ChromaConfig.load(path)

    def save_config(self, path: str = "chroma_config.json"):
        """_summary_
        Saves the current configuration settings of the ChromaStore instance to a JSON file.

        Args:
            path (str, optional): The path to the JSON configuration file. Defaults to "chroma_config.json".
        """        
        config = ChromaConfig()
        config.save(path)
       
    # endregion Configuration