"""Generate ota_manifest.json for the device's self-update.

Run before committing device-facing changes:
    python tools/make_ota_manifest.py
The version is the short git hash of HEAD plus staged-tree awareness:
commit first, then run this, then commit the manifest (the release
commit). Files listed are exactly what lives on /flash.
"""

import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# repo path -> device path under /flash (default: same path)
DEVICE_FILES = {
    "main.py": "main.py",
    "config.py": "config.py",
    "scheduler.py": "scheduler.py",
    "ui_renderer.py": "ui_renderer.py",
    "weather_service.py": "weather_service.py",
    "scoring_engine.py": "scoring_engine.py",
    "recommendation_engine.py": "recommendation_engine.py",
    "wonder_engine.py": "wonder_engine.py",
    "adventures.py": "adventures.py",
    "events.py": "events.py",
    "artwork.py": "artwork.py",
    "ota.py": "ota.py",
}
SCENE_DIRS = ("scenes/v3", "scenes/special")


def main():
    files, dest = {}, {}
    paths = dict(DEVICE_FILES)
    for d in SCENE_DIRS:
        full = os.path.join(ROOT, d)
        for name in sorted(os.listdir(full)):
            if name.endswith(".png"):
                rel = "%s/%s" % (d, name)
                paths[rel] = rel
    for rel, dev in sorted(paths.items()):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("  skip (missing):", rel)
            continue
        # Hash the COMMITTED bytes (what raw.githubusercontent
        # serves), not the working tree: Windows CRLF on disk vs LF
        # in git made the device reject config.py with a mismatch.
        data = subprocess.check_output(
            ["git", "show", "HEAD:" + rel.replace("\\", "/")],
            cwd=ROOT)
        files[rel] = hashlib.sha256(data).hexdigest()
        if dev != rel:
            dest[rel] = dev

    version = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT).decode().strip()
    manifest = {"version": version, "files": files}
    if dest:
        manifest["dest"] = dest
    out = os.path.join(ROOT, "ota_manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print("manifest: version %s, %d files" % (version, len(files)))


if __name__ == "__main__":
    main()
