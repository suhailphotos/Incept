# src/incept/utils/file_utils.py

import os
import re
import shutil
from pathlib import Path
from platformdirs import user_documents_dir

def get_default_documents_folder() -> Path:
    """
    Returns the cross-platform 'Documents' directory using platformdirs.
    On Windows, this typically points to:  C:\\Users\\<YourName>\\Documents
    On macOS:    /Users/<YourName>/Documents
    On Linux:    /home/<YourName>/Documents (or similar, if configured).
    """
    return Path(user_documents_dir())


def sanitize_dir_name(name: str) -> str:
    """
    Converts 'Course Name 123!' → 'Course_Name_123'
    - Spaces & dashes are converted to underscores.
    - Special characters (except `_`) are removed.
    - Ensures only **one** underscore (`_`) between words.
    """
    name = re.sub(r"[^\w\s-]", "", name)  # Remove special characters except space & dash
    name = name.replace("-", "_")         # Convert dashes to underscores
    name = re.sub(r"\s+", "_", name)      # Convert spaces to underscores
    name = re.sub(r"_+", "_", name)       # Remove multiple underscores
    return name.strip("_")  # Remove leading/trailing underscores


def sync_templates(src: Path, dst: Path):
    """
    Merge templates from `src` into `dst`:
      - If `dst/<folder>` does not exist, copy it from `src`.
      - If `dst/<folder>` is named 'default' (and already exists),
        remove it and copy fresh from `src`.
      - Otherwise (a custom folder), leave it in place.
    
    Also skips hidden/system files like .DS_Store, .gitkeep, etc.
    """
    if not src.exists():
        raise FileNotFoundError(f"Source templates folder does not exist: {src}")

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if item.name.startswith('.'):
            continue  # ignore hidden files/folders like .DS_Store

        dest_item = dst / item.name

        if item.is_dir():
            if not dest_item.exists():
                # Copy entire directory if it doesn't exist
                shutil.copytree(
                    item,
                    dest_item,
                    dirs_exist_ok=False,
                    ignore=shutil.ignore_patterns('.DS_Store', '.gitkeep')
                )
            else:
                # Overwrite if the folder is 'default'
                if item.name == "default":
                    shutil.rmtree(dest_item)
                    shutil.copytree(
                        item,
                        dest_item,
                        dirs_exist_ok=False,
                        ignore=shutil.ignore_patterns('.DS_Store', '.gitkeep')
                    )
                # Otherwise it's a custom folder => skip
        else:
            # It's a file, copy it only if it doesn't exist in `dst`
            if not dest_item.exists():
                shutil.copy2(item, dest_item)
