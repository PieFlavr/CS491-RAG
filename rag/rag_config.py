import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# ==============================================================================
#                                HOW THIS WORKS
# ==============================================================================
#
# Every config class (sub and root) is a BaseSettings, meaning each can:
#   - load from its own JSON file
#   - work fully standalone, w/o a higher-order orchestrator/configurator involved
#
# When RAGConfig (this submodule's orchestrator) loads, it reads the master JSON and passes
# each subsystem's section directly to the sub-config constructor. This bypasses
# the sub-config's own JSON file, making the master the single source of truth
# for that run (this is without sub-configs needing to know they're being orchestrated).
#
# Priority order (highest to lowest):
#   JSON file (or data passed by orchestrator)  >  coded defaults
#
# File layout:
#   rag_config.json             <-- master (used by RAGConfig and when orchestrated)
#   chroma_config.json          <-- standalone ChromaConfig
#   retriever_config.json       <-- standalone RetrieverConfig
#   loader_config.json          <-- standalone LoaderConfig
#
# Master JSON structure:
#   {
#     "chroma":    { "persist_dir": "data/chroma_db" },
#     "retriever": { "score_threshold": 0.5 },
#     "loader":    { "default_extension": ".html" }
#   }
# ==============================================================================

# region Sub-config Classes

class ChromaConfig(BaseSettings):
    """_summary_
    Subconfigurator for the ChromaDB vector store (chroma.py)
    Inherits from pydantic BaseSettings class.
    """

    model_config = SettingsConfigDict(
        json_file           = "chroma_config.json",
        json_file_encoding  = "utf-8",
        extra               = "ignore",
        frozen              = False,
    )

    persist_dir:     str       = "data/chroma_db"
    embedding_model: str       = "all-MiniLM-L6-v2"
    collections:     list[str] = ["quests", "lore"]

    @classmethod
    def load(cls, path: str = "chroma_config.json", _data: dict = {}) -> "ChromaConfig":
        """_summary_
        Loads the ChromaConfig either from its own JSON file or from a provided data dictionary (used by RAGConfig when orchestrating).
        
        Args:
            path (str, optional): The path to the JSON file to load from. Defaults to "chroma_config.json".
            _data (dict, optional): A dictionary containing configuration values to initialize the instance with. Defaults to {}.

        Returns:
            ChromaConfig: A populated configuration object created from the provided data or JSON file.
        """        
        if _data:
            return cls(**_data)
        if not os.path.exists(path):
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))

    def save(self, path: str = "chroma_config.json"):
        """_summary_
        Saves the current state of the ChromaConfig to a JSON file.
        
        Args:
            path (str, optional): The path to the JSON file to save to. Defaults to "chroma_config.json".
        """        
        _save(self, path)


class RetrieverConfig(BaseSettings):
    """_summary_
    Subconfigurator for the retriever (retriever.py)
    Inherits from pydantic BaseSettings class.
    """    

    model_config = SettingsConfigDict(
        json_file           = "retriever_config.json",
        json_file_encoding  = "utf-8",
        extra               = "ignore",
        frozen              = False,
    )

    score_threshold:  float = 0.3
    n_per_collection: int   = 3

    @classmethod
    def load(cls, path: str = "retriever_config.json", _data: dict = {}) -> "RetrieverConfig":
        """_summary_
        Loads the RetrieverConfig either from its own JSON file or from a provided data dictionary (used by RAGConfig when orchestrating).

        Args:
            path (str, optional): The path to the JSON file to load from. Defaults to "retriever_config.json".
            _data (dict, optional): A dictionary containing configuration values to initialize the instance with. Defaults to {}.

        Returns:
            RetrieverConfig: A populated configuration object created from the provided data or JSON file.
        """        
        if _data:
            return cls(**_data)
        if not os.path.exists(path):
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))

    def save(self, path: str = "retriever_config.json"):
        _save(self, path)


class LoaderConfig(BaseSettings):
    """_summary_
    Subconfigurator for the file ingestion pipeline (loader.py)
    Inherits from pydantic BaseSettings class.

    Since loader isn't a 'class', is instead dependecy-injected in the funcitons.
    """    

    model_config = SettingsConfigDict(
        json_file           = "loader_config.json",
        json_file_encoding  = "utf-8",
        extra               = "ignore",
        frozen              = False,
    )

    default_extension: str = ".html"
    encoding:          str = "utf-8"

    @classmethod
    def load(cls, path: str = "loader_config.json", _data: dict = {}) -> "LoaderConfig":
        """_summary_
        Loads the LoaderConfig either from its own JSON file or from a provided data dictionary (used by RAGConfig when orchestrating).

        Args:
            path (str, optional): The path to the JSON file to load from. Defaults to "loader_config.json".
            _data (dict, optional): A dictionary containing configuration values to initialize the instance with. Defaults to {}.

        Returns:
            LoaderConfig: A populated configuration object created from the provided data or JSON file.
        """        
        if _data:
            return cls(**_data)
        if not os.path.exists(path):
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls(**json.load(f))

    def save(self, path: str = "loader_config.json"):
        """_summary_

        Args:
            path (str, optional): The path to the JSON file to save to. Defaults to "loader_config.json".
        """        
        _save(self, path)

# endregion Sub-config Classes

# region Module Master Config

MASTER_CONFIG_PATH = "rag_config.json"


class RAGConfig(BaseSettings):
    """_summary_
    Root configuration for the RAG system. Composes all sub-configs for the RAG module. 
    Can be and highly recommended to recursively structure sister and parent module configs similarly. 

    Usage:
        config = RAGConfig.load()           # load from master JSON
        config = RAGConfig()                # all defaults, no file needed
        config.save()                       # write full resolved state to master JSON

        config.chroma.persist_dir           # access sub-config fields directly
        config.retriever.score_threshold
    """

    model_config = SettingsConfigDict(
        extra                = "ignore",
        frozen               = False,
    )

    # Sub-configs as fields. On a plain `RAGConfig()` call these just use their
    # own defaults — the orchestrator doesn't force a file read on standalone usage.
    chroma:    ChromaConfig    = ChromaConfig()
    retriever: RetrieverConfig = RetrieverConfig()
    loader:    LoaderConfig    = LoaderConfig()

    chroma_config_path: str = "chroma_config.json" 
    retriever_config_path: str = "retriever_config.json"  
    loader_config_path: str = "loader_config.json"


    @classmethod
    def load(cls, path: str = MASTER_CONFIG_PATH) -> "RAGConfig":
        """_summary_
        Loads the RAGConfig either from its own JSON file or from a provided data dictionary (used by the orchestrator).
        Reads the master JSON and passes each section down to the relevant sub-config. Sub-configs receive their data directly, 
        so their own JSON files are never touched during an orchestrated load.

        Args:
            path (str, optional): The path to the JSON file to load from. Defaults to MASTER_CONFIG_PATH.

        Returns:
            RAGConfig: A populated configuration object created from the provided data or JSON file.
        """

        if not os.path.exists(path):
            print(f"[RAGConfig] No master config at '{path}', using all defaults.")
            return cls()

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        instance = cls()

        chroma = ChromaConfig.load(path=instance.chroma_config_path, _data=data.get("chroma", {}))
        retriever = RetrieverConfig.load(path=instance.retriever_config_path, _data=data.get("retriever", {}))
        loader = LoaderConfig.load(path=instance.loader_config_path, _data=data.get("loader", {}))

        return cls(chroma=chroma, retriever=retriever, loader=loader)

    def save(self, path: str = MASTER_CONFIG_PATH):
        """_summary_
        Writes the full resolved state of all sub-configs to the master JSON.
        use this to snapshot exactly what a given run was configured with.

        Args:
            path (str, optional): The path to the JSON file to save to. Defaults to MASTER_CONFIG_PATH.
        """        
        data = {
            # config locations
            "chroma_config_path": self.chroma_config_path,
            "retriever_config_path": self.retriever_config_path,
            "loader_config_path": self.loader_config_path,

            # config data
            "chroma":    self.chroma.model_dump(mode="json"),
            "retriever": self.retriever.model_dump(mode="json"),
            "loader":    self.loader.model_dump(mode="json"),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[RAGConfig] Saved to '{path}'")

# endregion Module Master Config 


# region Shared Helpers
def _save(config: BaseSettings, path: str):
    """_summary_
    Saves the configuration to a JSON file.

    Args:
        config (BaseSettings): The configuration to save.
        path (str): The path to the JSON file to save to.
    """    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)
    print(f"[{type(config).__name__}] Saved to '{path}'")


# endregion Shared Helpers