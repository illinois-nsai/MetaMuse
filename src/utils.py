import json
import os


def write_to_file(dest_path: str, contents, is_append: bool, is_json: bool):
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    if is_append:
        if is_json:
            raise ValueError("append mode does not support JSON")
        with open(dest_path, "a") as file:
            file.write(contents)
        return

    if is_json:
        if not dest_path.endswith(".json"):
            raise ValueError("JSON output must end with .json")
        with open(dest_path, "w") as file:
            json.dump(contents, file, indent=4)
    else:
        with open(dest_path, "w") as file:
            file.write(contents)


def read_text(path: str) -> str:
    with open(path, "r") as file:
        return file.read()
