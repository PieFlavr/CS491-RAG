import os
import json
from rag.indexer import Indexer
from rag.manifest import Manifest
from rag.rag_config import LoaderConfig


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
    """
    if config is not None:
        encoding = config.encoding

    with open(filepath, "r", encoding=encoding) as f:
        return json.load(f)


def _scan_folder(folder: str, extension: str = ".json", config: LoaderConfig | None = None) -> list[str]:
    """_summary_
        Scans a folder and returns a list of file paths with the specified extension.
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
    if value is None:
        return ""
    return str(value).strip().lower()


def _load_coordinates(folder: str, config: LoaderConfig | None = None) -> list:
    """Loads clean_json_coord.txt as a list of coordinate entries."""

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
    """Finds the best coordinate reference for a quest."""

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
    """Builds searchable document text from one quest entry."""

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
    """Builds metadata for Chroma from quest data and coordinate lookup."""

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
        Ingests JSON quest files from a folder into a specified collection.
        Uses clean_json_coord.txt in the same folder to attach coordinates.
        Skips files that have already been ingested unless force=True.
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