"""
### This module holds the paths for all logs and data files.

These live here instead of in `main.py` so that both `main.py` and the modules it
imports (e.g. `backend/miscellaneous.py`) can use them without a circular import.
"""

from os import path, getcwd

### ===============================================================================

### Get the current working directory dynamically
### NOTE: This means main.py/app.py have to be run from the root of the repository.
BASE_PATH = getcwd()
### Paths for logs and data files
LOG_DIR = path.join(BASE_PATH, "logs")
DATA_DIR = path.join(BASE_PATH, "frontend", "src", "data")
TIMESTAMP_DIR = path.join(DATA_DIR, "timestamps")
