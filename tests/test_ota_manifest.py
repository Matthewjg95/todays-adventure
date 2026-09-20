"""Ensure release verification rejects incomplete or corrupt manifests."""
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_ota_manifest import validate


class TestManifestValidation(unittest.TestCase):
    def setUp(self):
        self.data = {"main.py": b"main", "scenes/v3/clear.png": b"scene"}
        self.expected = {p: p for p in self.data}
        self.manifest = {"version": "abc1234", "files": {
            p: hashlib.sha256(b).hexdigest() for p, b in self.data.items()}}

    def check(self):
        return validate(self.manifest, self.expected, self.data.__getitem__)

    def test_matching_release(self):
        self.assertEqual(self.check(), [])

    def test_changed_payload(self):
        self.data["main.py"] = b"changed"
        self.assertIn("hash mismatch: main.py", self.check())

    def test_missing_scene(self):
        del self.manifest["files"]["scenes/v3/clear.png"]
        self.assertIn("missing file: scenes/v3/clear.png", self.check())

    def test_unexpected_boot_file(self):
        self.manifest["files"]["boot.py"] = "x"
        self.assertIn("unexpected file: boot.py", self.check())

    def test_wrong_destination(self):
        self.manifest["dest"] = {"main.py": "boot.py"}
        self.assertIn("wrong destination: main.py", self.check())

    def test_empty_version(self):
        self.manifest["version"] = ""
        self.assertTrue(self.check())

    def test_malformed_files(self):
        self.manifest["files"] = []
        self.assertIn("files must be an object", self.check())

    def test_unreadable_payload(self):
        def missing(path):
            raise OSError("missing")
        self.assertTrue(any("unreadable" in e for e in
                            validate(self.manifest, self.expected, missing)))
