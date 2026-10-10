"""Gemini edition pass and notes upload pipeline (both off by default)."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import edition  # noqa: E402
import gemini_editor as ge  # noqa: E402
import notebook  # noqa: E402
import notes_sync  # noqa: E402

NOW = 1791450000


def built_edition():
    return {"format": edition.FORMAT, "generated": NOW, "id": "t",
            "sections": {
                "top": [{"title": "Outlet headline %d" % i, "summary": "Feed text %d." % i,
                         "source": "NPR"} for i in range(4)],
                "local": [{"title": "Local %d" % i, "summary": "", "source": "L"}
                          for i in range(2)]}}


def gemini_post(reply, status=200):
    def post(url, headers, body, timeout):
        post.calls.append((url, headers, json.loads(body)))
        envelope = {"candidates": [{"content": {"parts": [{"text": json.dumps(reply)}]}}]}
        return status, json.dumps(envelope)
    post.calls = []
    return post


class TestGeminiEditor(unittest.TestCase):
    def test_reorders_and_labels_without_touching_headlines(self):
        reply = {"sections": {"top": [{"id": "top-2", "summary": "Short take."},
                                      {"id": "top-0", "summary": ""}],
                              "local": [{"id": "local-1", "summary": "Local take."}]}}
        post = gemini_post(reply)
        out = ge.edit(built_edition(), "KEY", "test-model", post=post, log=lambda m: None)
        top = out["sections"]["top"]
        self.assertEqual([t["title"] for t in top], ["Outlet headline 2", "Outlet headline 0"])
        self.assertEqual(top[0]["summary"], "Short take." + ge.SUMMARY_TAG)
        self.assertEqual(top[1]["summary"], "Feed text 0.")      # no AI text: original kept
        self.assertEqual(out["edited_by"], "gemini")
        url, headers, body = post.calls[0]
        self.assertIn("test-model:generateContent", url)
        self.assertEqual(headers["x-goog-api-key"], "KEY")
        self.assertNotIn("KEY", url)                              # key never in the URL
        self.assertIn("Outlet headline 3", body["contents"][0]["parts"][0]["text"])

    def test_invented_or_foreign_ids_are_ignored(self):
        reply = {"sections": {"top": [{"id": "top-9", "summary": "invented"},
                                      {"id": "local-0", "summary": "moved"},
                                      {"id": "top-1", "summary": "ok"},
                                      {"id": "top-1", "summary": "dup"}]}}
        out = ge.edit(built_edition(), "K", post=gemini_post(reply), log=lambda m: None)
        self.assertEqual([t["title"] for t in out["sections"]["top"]], ["Outlet headline 1"])
        # local was not answered: the original section is kept whole
        self.assertEqual(out["sections"]["local"], built_edition()["sections"]["local"])

    def test_failures_publish_the_feed_edition(self):
        original = built_edition()
        for post in (gemini_post({}, status=429), gemini_post({"nope": 1}),
                     lambda *a: (200, "not json")):
            self.assertEqual(ge.edit(original, "K", post=post, log=lambda m: None), original)

    def test_summaries_are_cleaned_and_capped(self):
        reply = {"sections": {"top": [{"id": "top-0", "summary": "“x” " * 300}]}}
        out = ge.edit(built_edition(), "K", post=gemini_post(reply), log=lambda m: None)
        s = out["sections"]["top"][0]["summary"]
        self.assertLessEqual(len(s), edition.MAX_SUMMARY)
        self.assertTrue(s.endswith(ge.SUMMARY_TAG))
        self.assertTrue(all(32 <= ord(c) < 127 for c in s))
        edition.validate(out, NOW)

    def test_workflow_is_off_unless_variable_and_secret(self):
        with open(os.path.join(ROOT, ".github", "workflows", "edition.yml")) as f:
            wf = f.read()
        self.assertIn('[ "$GEMINI_EDITION" = "on" ] && [ -n "$GEMINI_API_KEY" ]', wf)
        self.assertEqual(wf.count("cron:"), 2)                   # two editions a day


class TestNotesSync(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.store = notebook.NotebookStore(os.path.join(self.dir, "notes"))
        self.state = os.path.join(self.dir, "notes_sync.json")

    def note(self, nid="n0001", t=100):
        n = notebook.Note(nid, 540, 790, 1)
        n.begin_stroke(100, 100, 0)
        n.add_point(300, 100, 20)
        n.end_stroke()
        self.store.save(n, t)
        return n

    def test_png_is_a_real_image_with_the_ink(self):
        from PIL import Image
        png = notes_sync.rasterize_png(self.note())
        img = Image.open(io.BytesIO(png))
        img.load()                                   # verifies CRCs and zlib stream
        self.assertEqual(img.size, (540, 790))
        self.assertEqual(img.mode, "1")
        self.assertEqual(img.getpixel((200, 100)), 0)    # ink is black
        self.assertEqual(img.getpixel((200, 400)), 255)  # paper is white

    def test_uploads_changed_notes_once(self):
        self.note("n0001")
        self.note("n0002")
        sent = []

        def post(url, body):
            data = json.loads(body)
            sent.append(data["note"]["note_id"])
            self.assertEqual(data["token"], "TOKEN")
            self.assertTrue(data["png_base64"])
            return 200, {}, json.dumps({"ok": True, "title": "x"})
        n = notes_sync.sync(self.store, "URL", "TOKEN", post, state_path=self.state,
                            log=lambda m: None)
        self.assertEqual((n, sent), (2, ["n0001", "n0002"]))
        self.assertEqual(notes_sync.sync(self.store, "URL", "TOKEN", post,
                                         state_path=self.state, log=lambda m: None), 0)
        self.note("n0002", t=200)                    # edited later: goes again
        notes_sync.sync(self.store, "URL", "TOKEN", post, state_path=self.state,
                        log=lambda m: None)
        self.assertEqual(sent[-1], "n0002")

    def test_apps_script_redirect_is_followed_for_the_result(self):
        self.note()

        def post(url, body):
            return 302, {"Location": "https://result"}, ""

        def get(url):
            self.assertEqual(url, "https://result")
            return 200, {}, json.dumps({"ok": True})
        self.assertEqual(notes_sync.sync(self.store, "U", "T", post, get,
                                         state_path=self.state, log=lambda m: None), 1)

    def test_failure_keeps_note_pending_and_stops(self):
        self.note("n0001")
        self.note("n0002")
        calls = []

        def post(url, body):
            calls.append(1)
            return 200, {}, json.dumps({"ok": False, "error": "unauthorized"})
        self.assertEqual(notes_sync.sync(self.store, "U", "T", post, state_path=self.state,
                                         log=lambda m: None), 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(notes_sync.pending(self.store, notes_sync.load_state(self.state))), 2)

    def test_not_wired_into_the_device_yet(self):
        with open(os.path.join(ROOT, "main.py")) as f:
            self.assertNotIn("notes_sync", f.read())
        from make_ota_manifest import DEVICE_FILES
        self.assertNotIn("notes_sync.py", DEVICE_FILES)


if __name__ == "__main__":
    unittest.main()
