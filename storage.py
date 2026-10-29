"""Read and write JSON while protecting an existing saved session."""

import json
import os
from pathlib import Path
import tempfile

from transactions import new_state, validate_state


def upgrade_saved_data(state):
    """Recognize old JSON sessions without changing their balances or history."""
    if type(state) is not dict:
        return state
    if "schema_version" not in state:
        return state

    version = state["schema_version"]
    if type(version) is not int:
        return state
    if version != 1:
        return state

    # Version 1 had no setup flag. Existing sessions count as already initialized.
    if "setup_complete" in state:
        raise ValueError("Unexpected setup field in a version 1 file.")
    upgraded = state.copy()
    upgraded["schema_version"] = 2
    upgraded["setup_complete"] = True
    return upgraded


def load_data(path):
    """Read a JSON file and return it only after the contents pass validation."""
    try:
        file_path = Path(path)
        file_path = file_path.expanduser()

        with open(file_path, "r", encoding="utf-8") as file:
            state = json.load(file)

        state = upgrade_saved_data(state)

        # A readable JSON file is not necessarily valid MoneyPilot data.
        validate_state(state)
        return state

    except (OSError, ValueError, TypeError, RecursionError) as error:
        # The menu can show one clear message for file and data errors.
        raise ValueError(f"Could not load: {error}")


def load_or_create_data(path):
    """Load the existing session, or create an empty file on the first run."""
    file_path = Path(path)
    file_path = file_path.expanduser()

    if file_path.exists():
        # Let errors reach main(). Never replace a damaged file with empty data.
        saved_state = load_data(file_path)
        return saved_state

    empty_state = new_state()
    save_data(empty_state, file_path)
    return empty_state


def save_data(state, path):
    """Finish a temporary JSON file before replacing the saved data file."""
    temporary_path = None

    try:
        # Check data before writing anything to disk.
        validate_state(state)

        target_path = Path(path)
        target_path = target_path.expanduser()
        target_folder = target_path.parent

        # A temporary file prevents an incomplete write from damaging old data.
        # Put it in the same folder so the final replacement stays on one disk.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_folder,
            delete=False,
        ) as file:
            temporary_path = file.name

            # Indentation makes the JSON readable; UTF-8 keeps Thai text readable.
            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            file.write("\n")

        # The with block has closed the completed file before this replacement.
        os.replace(temporary_path, target_path)

    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise ValueError(f"Could not save: {error}")

    finally:
        # Remove a leftover temporary file after a failure.
        # After a successful replacement, the temporary name no longer exists.
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
