# src/incept/config.py

from pathlib import Path
from dotenv import load_dotenv

# 1) Try a “local” .env sitting next to this file (for ad‑hoc tests)
_local = Path(__file__).parent / ".env"
if _local.is_file():
    load_dotenv(dotenv_path=_local, override=False)

# 2) Then load the “official” ~/.incept/.env (won’t override anything from local)
_home = Path.home() / ".incept" / ".env"
load_dotenv(dotenv_path=_home, override=False)
