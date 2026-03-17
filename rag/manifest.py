import json
import os
from datetime import datetime


MANIFEST_FILENAME = "manifest.json"


class Manifest:
    """
    Tracks which files have been ingested into the database.
    For now lives in the same folder as the ChromaDB data, so the entire db can be deleted/zipped and shared easy.

    manifest.json looks like:
    {
        "ashenvale.html": {
            "ingested_at": "2024-03-16T10:32:00",
            "collection": "lore"
        }
    }
    """

    def __init__(self, chroma_dir: str = "./data/chroma_db"):
        self.path = os.path.join(chroma_dir, MANIFEST_FILENAME)
        self._data = self._load()

    def _load(self) -> dict:
        """Loads manifest from disk, or returns empty dict if it doesn't exist yet."""
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Writes current manifest state to disk."""
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def record(self, filename: str, collection: str):
        """
        Marks a file as ingested.
        filename:   just the filename e.g. "ashenvale.html"
        collection: which collection it went into
        """
        self._data[filename] = {
            "ingested_at": datetime.now().isoformat(),
            "collection": collection
        }
        self._save()

    def is_ingested(self, filename: str) -> bool:
        """Returns True if this file has already been ingested."""
        return filename in self._data

    def remove(self, filename: str):
        """Removes a file from the manifest so it can be re-ingested."""
        if filename in self._data:
            del self._data[filename]
            self._save()

    def clear(self):
        """Wipes the entire manifest."""
        self._data = {}
        self._save()

    def all(self) -> dict:
        """Returns everything in the manifest."""
        return self._data