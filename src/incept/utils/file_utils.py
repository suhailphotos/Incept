# src/incept/utils/file_utils.py

import shutil
from pathlib import Path

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
