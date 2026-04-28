import os
import json
from .indexer import Indexer
from .manifest import Manifest
from .rag_config import LoaderConfig


COORD_FILE_NAME = "clean_json_coord.txt"


def _get_id(filepath: str, config: LoaderConfig | None = None) -> str:
    """
    Generates a document ID from a filename
    e.g. "data.json" -> "data"
    """
    if config is not None:
        # add any custom ID generation logic here using config if needed
        pass
    return os.path.splitext(os.path.basename(filepath))[0]


def _read_json(filepath: str, encoding: str = "utf-8", config: LoaderConfig | None = None):
    """_summary_
        Reads a JSON file and returns the loaded data.

    Args:
        filepath (str): The path to the JSON file to read.
        encoding (str, optional): The file encoding to use when reading the JSON file. Defaults to "utf-8".
        config (LoaderConfig | None, optional): If not None, overrides default encoding with config values. Defaults to None.

    Returns:
        Any: The parsed JSON data.
    """
    if config is not None:
        encoding = config.encoding

    with open(filepath, "r", encoding=encoding) as f:
        return json.load(f)


def _scan_folder(folder: str, extension: str = ".json", config: LoaderConfig | None = None) -> list[str]:
    """_summary_
        Scans a folder and returns a list of file paths with the specified extension.

    Args:
        folder (str): The path to the folder to scan.
        extension (str, optional): The file extension to look for. Defaults to ".json".
        config (LoaderConfig | None, optional): If not None, overrides default extension with config.default_extension. Defaults to None.

    Returns:
        list[str]: A list of file paths with the specified extension found in the folder.
    """

    if config is not None:
        extension = config.default_extension

    print("Scanning folder:", folder)
    print("Files found:", os.listdir(folder))

    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(extension)
    ]


def _safe_metadata_value(value):
    """_summary_
        Coerces a value into a Chroma-safe metadata string.
        None becomes an empty string, lists and dicts are JSON-serialised,
        and everything else is cast to str.

    Args:
        value: The raw metadata value to sanitise.

    Returns:
        str: A Chroma-compatible string representation of the value.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        if len(value) == 0:
            return ""
        return json.dumps(value)
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def _clean_text(value):
    """_summary_
        Normalises a value to a lowercase, stripped string for fuzzy matching.
        None becomes an empty string.

    Args:
        value: The value to normalise.

    Returns:
        str: The lowercased and whitespace-stripped string representation.
    """
    if value is None:
        return ""
    return str(value).strip().lower()


def _load_coordinates(folder: str, config: LoaderConfig | None = None) -> list:
    """_summary_
        Loads the coordinate reference file (clean_json_coord.txt) from the given folder
        and returns its contents as a list of coordinate entries.

    Args:
        folder (str): The path to the folder containing clean_json_coord.txt.
        config (LoaderConfig | None, optional): If not None, passed through to _read_json for encoding overrides. Defaults to None.

    Returns:
        list: A list of coordinate entry dicts, or an empty list if the file is missing or malformed.
    """

    coord_path = os.path.join(folder, COORD_FILE_NAME)

    if not os.path.exists(coord_path):
        print("Coordinate file not found:", coord_path)
        return []

    coord_data = _read_json(coord_path, config=config)

    if not isinstance(coord_data, list):
        print("Coordinate file is not a list:", coord_path)
        return []

    return coord_data


def _find_coordinate_for_quest(quest_name: str, quest_data: dict, coord_data: list) -> dict:
    """_summary_
        Finds the best matching coordinate entry for a given quest by trying three
        strategies in order: exact name match, coord name appearing in the walkthrough,
        and quest name appearing in the coord description.

    Args:
        quest_name (str): The name of the quest to match.
        quest_data (dict): The quest data dict, expected to contain a "Walkthrough" key.
        coord_data (list): The list of coordinate entry dicts loaded from clean_json_coord.txt.

    Returns:
        dict: The best matching coordinate entry, or an empty dict if no match is found.
    """

    walkthrough = quest_data.get("Walkthrough", "")
    quest_name_clean = _clean_text(quest_name)
    walkthrough_clean = _clean_text(walkthrough)

    # 1. Exact quest-name match
    for coord in coord_data:
        coord_name = _clean_text(coord.get("name", ""))

        if coord_name == quest_name_clean:
            return coord

    # 2. Coordinate name appears in walkthrough
    for coord in coord_data:
        coord_name = _clean_text(coord.get("name", ""))

        if coord_name != "" and coord_name in walkthrough_clean:
            return coord

    # 3. Coordinate description mentions the quest name
    for coord in coord_data:
        coord_description = _clean_text(coord.get("description", ""))

        if quest_name_clean != "" and quest_name_clean in coord_description:
            return coord

    return {}


def _build_quest_text(quest_name: str, quest_data: dict) -> str:
    """_summary_
        Builds the searchable document text for a single quest entry,
        combining the quest name, objectives, and walkthrough into a
        structured, newline-separated string.

    Args:
        quest_name (str): The name of the quest.
        quest_data (dict): The quest data dict, expected to contain "Objectives" and "Walkthrough" keys.

    Returns:
        str: The formatted document text to be indexed.
    """

    walkthrough = quest_data.get("Walkthrough", "")
    objectives = quest_data.get("Objectives", {})

    text_parts = []

    text_parts.append(f"Quest Name: {quest_name}")

    if objectives:
        text_parts.append(f"Objectives: {json.dumps(objectives)}")

    if walkthrough:
        text_parts.append(f"Walkthrough: {walkthrough}")

    return "\n\n".join(text_parts)


def _build_quest_metadata(filename: str, quest_name: str, quest_data: dict, coord_data: list) -> dict:
    """_summary_
        Builds the Chroma metadata dict for a single quest entry, including source file,
        quest name, walkthrough, and any coordinate fields resolved via _find_coordinate_for_quest.

    Args:
        filename (str): The source filename to record in metadata.
        quest_name (str): The name of the quest.
        quest_data (dict): The quest data dict, expected to contain a "Walkthrough" key.
        coord_data (list): The list of coordinate entry dicts loaded from clean_json_coord.txt.

    Returns:
        dict: A flat dict of Chroma-safe metadata strings for the quest.
    """

    walkthrough = quest_data.get("Walkthrough", "")
    matched_coord = _find_coordinate_for_quest(quest_name, quest_data, coord_data)

    return {
        "source": _safe_metadata_value(filename),
        "quest_name": _safe_metadata_value(quest_name),
        "Walkthrough": _safe_metadata_value(walkthrough),
        "objective_x": _safe_metadata_value(matched_coord.get("x")),
        "objective_y": _safe_metadata_value(matched_coord.get("y")),
        "coord_name": _safe_metadata_value(matched_coord.get("name")),
        "coord_category": _safe_metadata_value(matched_coord.get("category")),
        "coord_description": _safe_metadata_value(matched_coord.get("description"))
    }


def preview_folder(folder: str, collection: str, extension: str = ".json", config: LoaderConfig | None = None):
    """
    Scans a folder and prints a preview of what would be ingested.
    Does NOT write anything to the database.
    """
    files = _scan_folder(folder, extension, config)
    coord_data = _load_coordinates(folder, config)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    print(f"Found {len(files)} file(s) to ingest into '{collection}':\n")

    for filepath in files:
        filename = os.path.basename(filepath)

        if filename == COORD_FILE_NAME:
            continue

        data = _read_json(filepath, config=config)

        if not isinstance(data, dict):
            print("Skipping non-quest JSON file:", filename)
            continue

        for quest_name, quest_data in data.items():
            text = _build_quest_text(quest_name, quest_data)
            metadata = _build_quest_metadata(filename, quest_name, quest_data, coord_data)
            preview = text[:200].replace("\n", " ")

            print(f"  Quest:   {quest_name}")
            print(f"  Preview: {preview}...")
            print(f"  Metadata: {metadata}")
            print()


def ingest_folder(
    folder: str,
    collection: str,
    indexer: Indexer,
    manifest: Manifest = Manifest(),
    force: bool = False,
    extension: str = ".json",
    config: LoaderConfig | None = None
):
    """_summary_
        Ingests JSON quest files from a folder into a specified collection, using the provided
        indexer and manifest to track ingested files. Uses clean_json_coord.txt in the same
        folder to attach coordinates to each quest. Skips files that have already been ingested
        unless force=True.

    Args:
        folder (str): The path to the folder containing JSON quest files to ingest.
        collection (str): The name of the collection into which to ingest the quests.
        indexer (Indexer): The indexer instance to use for writing the documents.
        manifest (Manifest, optional): The manifest instance to check and update. Defaults to Manifest().
        force (bool, optional): If True, re-ingests files already in the manifest. Defaults to False.
        extension (str, optional): The file extension to look for. Defaults to ".json".
        config (LoaderConfig | None, optional): The loader config instance to use for loading files. Defaults to None.
    """

    files = _scan_folder(folder, extension, config)
    coord_data = _load_coordinates(folder, config)

    if not files:
        print(f"No {extension} files found in: {folder}")
        return

    new_files = []
    skipped = []

    for filepath in files:
        filename = os.path.basename(filepath)

        if filename == COORD_FILE_NAME:
            continue

        if not force and manifest and manifest.is_ingested(filename):
            skipped.append(filename)
        else:
            new_files.append(filepath)

    if skipped:
        print(f"Skipping {len(skipped)} already ingested file(s):")
        for f in skipped:
            print(f"  {f}")
        print()

    if not new_files:
        print("Nothing new to ingest.")
        return

    docs = []

    for filepath in new_files:
        base_doc_id = _get_id(filepath, config)
        data = _read_json(filepath, config=config)
        filename = os.path.basename(filepath)

        if not isinstance(data, dict):
            print("Skipping non-quest JSON file:", filename)
            continue

        for quest_name, quest_data in data.items():
            text = _build_quest_text(quest_name, quest_data)
            metadata = _build_quest_metadata(filename, quest_name, quest_data, coord_data)

            print("Preparing quest:", quest_name)
            print("Metadata prepared.")

            docs.append({
                "id": f"{base_doc_id}_{quest_name}",
                "text": text,
                "metadata": metadata
            })

        manifest.record(filename, collection)

    indexer.add_bulk(collection, docs)

    print(f"Ingested {len(docs)} quest(s) into '{collection}'. DB is stable.")