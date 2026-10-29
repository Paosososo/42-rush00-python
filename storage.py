"""Save JSON, and validate loaded data before using it."""

import json
import os
from pathlib import Path
import tempfile

from transactions import validate_state


def load_data(path):
    try:
        with open(Path(path).expanduser(), encoding="utf-8") as file:
            state = json.load(file)
        validate_state(state)
        return state
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise ValueError(f"Could not load: {error}") from None


def save_data(state, path):
    temporary_path = None
    try:
        validate_state(state)
        target = Path(path).expanduser()
        # Write a complete temporary file before replacing an existing save.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=target.parent, delete=False) as file:
            temporary_path = file.name
            json.dump(state, file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write("\n")
        os.replace(temporary_path, target)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise ValueError(f"Could not save: {error}") from None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
