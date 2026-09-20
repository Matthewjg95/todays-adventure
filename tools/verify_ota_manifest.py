"""Read-only check that OTA covers the release files and their committed bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from make_ota_manifest import DEVICE_FILES, SCENE_DIRS


def validate(manifest, expected, read_bytes):
    errors = []
    if not isinstance(manifest.get("version"), str) or not manifest["version"].strip():
        errors.append("version must be a nonempty string")
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        return errors + ["files must be an object"]
    for path in sorted(set(expected) - set(files)):
        errors.append("missing file: " + path)
    for path in sorted(set(files) - set(expected)):
        errors.append("unexpected file: " + path)
    destinations = manifest.get("dest", {})
    if not isinstance(destinations, dict):
        return errors + ["dest must be an object"]
    for path in sorted(set(destinations) - set(expected)):
        errors.append("unexpected destination: " + path)
    for path in sorted(set(files) & set(expected)):
        if destinations.get(path, path) != expected[path]:
            errors.append("wrong destination: " + path)
        try:
            actual = hashlib.sha256(read_bytes(path)).hexdigest()
        except (OSError, subprocess.CalledProcessError):
            errors.append("unreadable committed file: " + path)
            continue
        if actual != files[path]:
            errors.append("hash mismatch: " + path)
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "ota_manifest.json").read_text(encoding="utf-8"))
    expected = dict(DEVICE_FILES)
    for directory in SCENE_DIRS:
        for path in (root / directory).glob("*.png"):
            rel = path.relative_to(root).as_posix()
            expected[rel] = rel
    def committed(path):
        return subprocess.check_output(["git", "show", "HEAD:" + path], cwd=root)
    errors = validate(manifest, expected, committed)
    for error in errors:
        print("ERROR:", error)
    if errors:
        return 1
    print("OTA verified: %s, %d files (committed HEAD bytes)" %
          (manifest["version"], len(expected)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
