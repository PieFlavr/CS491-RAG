import os
from bs4 import BeautifulSoup
from rag.indexer import Indexer
from rag.manifest import Manifest
from rag_config import LoaderConfig


def _get_id(filepath: str, config: LoaderConfig | None = None) -> str:
    """
    Generates a document ID from a filename (replace w/ smarter scheme later)
    e.g. "test.html" -> "test"
    """
    if config is not None:
        # add any custom ID generation logic here using config if needed
        pass
    return os.path.splitext(os.path.basename(filepath))[0]


def _read_html(filepath: str, encoding: str = "utf-8", parser: str = "html.parser", config: LoaderConfig | None = None) -> str:
    """_summary_
        Reads an HTML file and extracts the text content.
    
    Args:
        filepath (str): The path to the HTML file to read.
        encoding (str, optional): The file encoding to use when reading the HTML file. Defaults to "utf-8".
        parser (str, optional): The parser to use when parsing the HTML file. Defaults to "html.parser".
        config (LoaderConfig | None, optional): If not None, overrides default encoding and parser with config values. Defaults to None.

    Returns:
        str: The extracted text content from the files.
    """    
    if config is not None:
        encoding = config.encoding
        # !TODO add a parser config here

    with open(filepath, "r", encoding=encoding) as f:
        soup = BeautifulSoup(f.read(), parser)
        return soup.get_text(separator=" ", strip=True)


def _scan_folder(folder: str, extension: str = ".html", config: LoaderConfig | None = None) -> list[str]:
    """_summary_
        Scans a folder and returns a list of file paths with the specified extension.
    
    Args:
        folder (str): The path to the folder to scan.
        extension (str, optional): The file extension to look for. Defaults to ".html".
        config (LoaderConfig | None, optional): If not None, overrides default extension with config.default_extension. Defaults to None.

    Returns:
        list[str]: A list of file paths with the specified extension found in the folder.
    """ 

    if config is not None:
        extension = config.default_extension

    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(extension)
    ]


def preview_folder(folder: str, collection: str, extension: str = ".html", config: LoaderConfig | None = None):
    """
    Scans a folder and prints a preview of what would be ingested.
    Does NOT write anything to the database.
    """
    files = _scan_folder(folder, extension, config)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    print(f"Found {len(files)} file(s) to ingest into '{collection}':\n")
    for filepath in files:
        doc_id = _get_id(filepath, config)
        text = _read_html(filepath, config=config)
        preview = text[:200].replace("\n", " ")
        print(f"  ID:      {doc_id}")
        print(f"  Preview: {preview}...")
        print()


def ingest_folder(
    folder: str,
    collection: str,
    indexer: Indexer,
    manifest: Manifest = Manifest(),
    force: bool = False,
    extension: str = ".html",
    config: LoaderConfig | None = None
):
    """_summary_
        Ingests files from a folder into a specified collection, using the provided indexer and manifest to track ingested files.
        Skips files that have already been ingested unless force=True.

    Args:
        folder (str): The path to the folder containing files to ingest.
        collection (str): The name of the collection into which to ingest the files.
        indexer (Indexer): The indexer instance to use for writing the files.
        manifest (Manifest, optional): The manifest instance to check and update. Defaults to Manifest().
        force (bool, optional): If True, re-ingests files already in the manifest. Defaults to False.
        extension (str, optional): The file extension to look for. Defaults to ".html".
        config (LoaderConfig | None, optional): The loader config instance to use for loading files. Defaults to None.
    """


    files = _scan_folder(folder, extension, config)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    new_files    = []
    skipped      = []

    for filepath in files:
        filename = os.path.basename(filepath)
        if not force and manifest and manifest.is_ingested(filename):
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
        doc_id   = _get_id(filepath, config)
        text     = _read_html(filepath, config=config)
        filename = os.path.basename(filepath)
        docs.append({
            "id":       doc_id,
            "text":     text,
            "metadata": {"source": filename}
        })
        manifest.record(filename, collection)

    indexer.add_bulk(collection, docs)
    print(f"Ingested {len(docs)} new file(s) into '{collection}'. DB is stable.")