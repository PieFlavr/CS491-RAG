import os
from bs4 import BeautifulSoup
from rag.indexer import Indexer
from rag.manifest import Manifest


def _get_id(filepath: str) -> str:
    """
    Generates a document ID from a filename (replace w/ smarter scheme later)
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
    """
    files = _scan_folder(folder, extension)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    print(f"Found {len(files)} file(s) to ingest into '{collection}':\n")
    for filepath in files:
        doc_id = _get_id(filepath)
        text = _read_html(filepath)
        preview = text[:200].replace("\n", " ")
        print(f"  ID:      {doc_id}")
        print(f"  Preview: {preview}...")
        print()


def ingest_folder(
    folder: str,
    collection: str,
    indexer: Indexer,
    manifest: Manifest,
    force: bool = False,
    extension: str = ".html"
):
    """
    Ingests files from a folder into the database.
    Skips files already recorded in the manifest unless force=True.

    folder:     path to the folder to scan
    collection: "quests" or "lore"
    indexer:    Indexer instance to write with
    manifest:   Manifest instance to check and update
    force:      if True, re-ingests files already in the manifest
    extension:  file type to look for, defaults to .html
    """
    files = _scan_folder(folder, extension)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    new_files    = []
    skipped      = []

    for filepath in files:
        filename = os.path.basename(filepath)
        if not force and manifest.is_ingested(filename):
            skipped.append(filename)
        else:
            new_files.append(filepath)

    # report what will be skipped
    if skipped:
        print(f"Skipping {len(skipped)} already ingested file(s):")
        for f in skipped:
            print(f"  {f}")
        print()

    if not new_files:
        print("Nothing new to ingest.")
        return

    # ingest new files
    docs = []
    for filepath in new_files:
        doc_id   = _get_id(filepath)
        text     = _read_html(filepath)
        filename = os.path.basename(filepath)
        docs.append({
            "id":       doc_id,
            "text":     text,
            "metadata": {"source": filename}
        })
        manifest.record(filename, collection)

    indexer.add_bulk(collection, docs)
    print(f"Ingested {len(docs)} new file(s) into '{collection}'. DB is stable.")