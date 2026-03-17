import os
from bs4 import BeautifulSoup # for HTML parsing
from rag.indexer import Indexer


def _get_id(filepath: str) -> str:
    """
    Generates a document ID from a filename (replace w/ smarter file name scheme later)
    e.g. "test.html" -> "test"
    """
    return os.path.splitext(os.path.basename(filepath))[0]


def _read_html(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        return soup.get_text(separator=" ", strip=True)


def _scan_folder(folder: str, extension: str = ".html") -> list[str]:
    """Returns a list of filepaths matching the extension in the given folder."""
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(extension)
    ]


def preview_folder(folder: str, collection: str, extension: str = ".html"):
    """
    Scans a folder and prints a preview of what would be ingested.
    Does NOT write anything to the database.

    folder:     path to the folder to scan
    collection: "quests" or "lore"
    extension:  file type to look for, defaults to .html
    """
    files = _scan_folder(folder, extension)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    print(f"Found {len(files)} file(s) to ingest into '{collection}':\n")
    for filepath in files:
        doc_id = _get_id(filepath)
        text = _read_html(filepath)
        preview = text[:200].replace("\n", " ")  # first 200 chars as preview
        print(f"  ID:      {doc_id}")
        print(f"  Preview: {preview}...")
        print()


def ingest_folder(folder: str, collection: str, indexer: Indexer, extension: str = ".html"):
    """
    Scans a folder, previews the files, asks for confirmation, then ingests.

    folder:     path to the folder to scan
    collection: "quests" or "lore"
    indexer:    Indexer instance to write with
    extension:  file type to look for, defaults to .html
    """
    files = _scan_folder(folder, extension)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    # preview first
    preview_folder(folder, collection, extension)

    # ingest
    docs = []
    for filepath in files:
        doc_id = _get_id(filepath)
        text = _read_html(filepath)
        docs.append({
            "id": doc_id,
            "text": text,
            "metadata": {"source": os.path.basename(filepath)}
        })

    indexer.add_bulk(collection, docs)
    print(f"\nIngested {len(docs)} file(s) into '{collection}'. DB is stable.")