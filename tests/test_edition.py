"""Daily Paper edition: companion build, device validation, layout fit."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_edition  # noqa: E402
import edition  # noqa: E402
import main  # noqa: E402
import newspaper as np  # noqa: E402
import ui_renderer  # noqa: E402

try:
    from preview_canvas import PILCanvas
except ImportError:
    PILCanvas = None

NOW = 1791450000

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Caf\xc3\xa9 opens on &lt;Main&gt; Street</title>
<description><![CDATA[<p>The <b>new</b> caf\xc3\xa9 \xe2\x80\x94 \xe2\x80\x9cfinally\xe2\x80\x9d.</p>]]></description></item>
<item><title>Second story</title><description>Plain summary.</description></item>
<item><title>  </title><description>no title, skipped</description></item>
<item><title>Third story</title><description>x</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom one</title><summary>Atom summary</summary></entry>
<entry><title>Cafe opens on Main Street!</title><summary>duplicate</summary></entry>
</feed>"""


def sample_edition(n=4, title="A headline about something", summary="A summary. " * 20):
    return {"format": edition.FORMAT, "generated": NOW, "id": "x",
            "sections": {s: [{"title": "%s %s %d" % (title, s, i), "summary": summary,
                              "source": "Src"} for i in range(n)]
                         for s in edition.SECTIONS}}


class TestBuilder(unittest.TestCase):
    def test_parse_rss_and_atom(self):
        items = build_edition.parse_feed(RSS)
        self.assertEqual(items[0][0], "Cafe opens on <Main> Street")
        self.assertIn("new cafe", items[0][1])
        self.assertEqual(len(items), 3)
        self.assertEqual(build_edition.parse_feed(ATOM)[0], ("Atom one", "Atom summary"))

    def test_build_dedups_caps_and_survives_a_bad_feed(self):
        feeds = {"a": RSS, "b": ATOM}

        def fetch(url):
            if url == "bad":
                raise OSError("down")
            return feeds[url]
        sources = [{"section": "top", "name": "A", "url": "a", "max": 2},
                   {"section": "world", "name": "Bad", "url": "bad"},
                   {"section": "tech", "name": "B", "url": "b", "summary": False},
                   {"section": "nope", "name": "X", "url": "a"}]
        data = build_edition.build(sources, fetch, now=NOW, log=lambda m: None)
        self.assertEqual([i["title"] for i in data["sections"]["top"]],
                         ["Cafe opens on <Main> Street", "Second story"])
        self.assertEqual(data["sections"]["top"][0]["summary"],
                         'The new cafe - "finally".')
        self.assertNotIn("world", data["sections"])
        tech = data["sections"]["tech"]
        self.assertEqual([i["title"] for i in tech], ["Atom one"])   # duplicate dropped
        self.assertEqual(tech[0]["summary"], "")
        self.assertEqual(data["sources"], {"top": ["A"], "tech": ["B"]})
        edition.validate(data, NOW)

    def test_all_feeds_failing_publishes_nothing(self):
        def fetch(url):
            raise OSError("offline")
        with self.assertRaises(edition.EditionError):
            build_edition.build([{"section": "top", "name": "A", "url": "a"}],
                                fetch, now=NOW, log=lambda m: None)

    def test_sources_file_is_valid(self):
        with open(os.path.join(ROOT, "tools", "edition_sources.json")) as f:
            sources = json.load(f)
        for s in sources:
            self.assertIn(s["section"], edition.SECTIONS)
            self.assertTrue(s["url"].startswith("https://"))


class TestDeviceValidation(unittest.TestCase):
    def test_cleans_and_caps(self):
        data = sample_edition(n=10, title="“Quoted” — 中文 title",
                              summary="word " * 200)
        data["sections"]["junk"] = [{"title": "ignored"}]
        data["sections"]["top"].insert(0, "not a dict")
        clean = edition.validate(data, NOW)
        self.assertNotIn("junk", clean["sections"])
        top = clean["sections"]["top"]
        self.assertEqual(len(top), edition.MAX_ITEMS)
        self.assertTrue(top[0]["title"].startswith('"Quoted" - title'))
        self.assertTrue(all(32 <= ord(c) < 127 for c in top[0]["title"]))
        self.assertLessEqual(len(top[0]["summary"]), edition.MAX_SUMMARY)
        self.assertTrue(top[0]["summary"].endswith("..."))

    def test_rejects(self):
        for bad in ({}, {"format": "other"},
                    {"format": edition.FORMAT, "generated": "yesterday", "sections": {}},
                    {"format": edition.FORMAT, "generated": NOW, "sections": {"top": []}},
                    {"format": edition.FORMAT, "generated": NOW + 99999,
                     "sections": {"top": [{"title": "t"}]}}):
            with self.assertRaises(edition.EditionError):
                edition.validate(bad, NOW)

    def test_staleness(self):
        ed = edition.validate(sample_edition(), NOW)
        self.assertFalse(edition.is_stale(ed, NOW + 3600))
        self.assertTrue(edition.is_stale(ed, NOW + 37 * 3600))


class TestFetch(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.path = os.path.join(self.dir, "edition.json")

    def get_json(self, data):
        return lambda url: json.dumps(data).encode()

    def test_store_and_reload(self):
        ed = edition.fetch_and_store("u", self.path, self.get_json(sample_edition()), NOW)
        self.assertEqual(edition.load_cached(self.path, NOW), ed)
        self.assertFalse(edition.needs_refresh(self.path, NOW + 60))
        self.assertTrue(edition.needs_refresh(self.path, NOW + 4 * 3600))

    def test_bad_download_keeps_good_cache(self):
        good = edition.fetch_and_store("u", self.path, self.get_json(sample_edition()), NOW)
        for get in (lambda u: b"<html>rate limited</html>",
                    lambda u: b"x" * (edition.MAX_BYTES + 1),
                    self.get_json({"format": "other"})):
            with self.assertRaises(edition.EditionError):
                edition.fetch_and_store("u", self.path, get, NOW)
        self.assertEqual(edition.load_cached(self.path, NOW), good)

    def test_older_download_does_not_replace_newer(self):
        newer = sample_edition()
        newer["generated"] = NOW + 100
        edition.fetch_and_store("u", self.path, self.get_json(newer), NOW + 200)
        got = edition.fetch_and_store("u", self.path, self.get_json(sample_edition()), NOW + 200)
        self.assertEqual(got["generated"], NOW + 100)

    def test_missing_cache_means_sample(self):
        self.assertIsNone(edition.load_cached(self.path, NOW))


class TestPaperWithNews(unittest.TestCase):
    def blocks(self, ed, stale=False):
        news = edition.validate(ed, NOW)["sections"]
        return np.build_edition(None, None, None, None, [], "Thursday, October 8",
                                news, "Edition of Thu, Oct 8, 6:17 AM", stale)

    def test_same_positions_as_sample(self):
        sample = np.build_edition()
        live = self.blocks(sample_edition())
        self.assertEqual([b[:5] for b in sample], [b[:5] for b in live])

    def check_fit(self, measure):
        for ed in (sample_edition(n=6), sample_edition(n=1, summary=""),
                   sample_edition(n=6, title="W " * 70, summary="long " * 80)):
            for block in self.blocks(ed):
                ops, used = np.typeset(block, measure)
                self.assertLessEqual(used, block[4], block[0])
                if block[0] == "masthead":
                    continue
                for kind, x, y, payload, size, _ in ops:
                    if kind == "text":
                        self.assertLessEqual(y + size, block[2] + block[4], (block[0], payload))
                        self.assertLessEqual(x + measure(payload, size),
                                             block[1] + block[3] + 2, payload)

    def test_long_content_is_cut_not_overflowed(self):
        self.check_fit(ui_renderer.TextCanvas().text_width)

    @unittest.skipIf(PILCanvas is None, "Pillow not installed")
    def test_fit_with_dejavu_metrics(self):
        self.check_fit(PILCanvas().text_width)

    def test_cut_text_ends_with_ellipsis(self):
        ed = sample_edition(n=1, summary="sentence " * 200)
        ops, _ = np.typeset([b for b in self.blocks(ed) if b[0] == "c10"][0],
                            ui_renderer.TextCanvas().text_width)
        texts = [o[3] for o in ops if o[0] == "text"]
        self.assertTrue(texts[-1].endswith("..."))

    def test_labels_and_titles(self):
        blocks = self.blocks(sample_edition())
        mast = blocks[0][5][0]
        self.assertEqual(mast[2], "TODAY'S EDITION")
        self.assertEqual(np.route_titles({"top": []}), np.NEWS_TITLES)
        stale = self.blocks(sample_edition(), stale=True)[0][5][0]
        self.assertEqual(stale[2], "OLDER EDITION")
        self.assertEqual(np.build_edition()[0][5][0][2], "SAMPLE EDITION")
        self.assertEqual(len(np.NEWS_TITLES), len(np.ROUTE))

    def test_no_story_appears_twice(self):
        seen = []
        for block in self.blocks(sample_edition(n=4)):
            for item in block[5]:
                if item[0] in ("head", "brief"):
                    seen.append(item[1])
        self.assertEqual(len(seen), len(set(seen)))

    def test_missing_section_says_so(self):
        ed = sample_edition()
        del ed["sections"]["local"]
        cell = dict((b[0], b[5]) for b in self.blocks(ed))["c22"]
        self.assertTrue(any("No local stories" in i[1] for i in cell if i[0] == "small"))


class TestMainHook(unittest.TestCase):
    def test_battery_gate_and_failure_is_logged_only(self):
        logs = []
        with mock.patch.object(main, "log_wake", side_effect=logs.append), \
                mock.patch.object(edition, "needs_refresh", return_value=True), \
                mock.patch.object(edition, "fetch_and_store", side_effect=OSError("offline")) as fetch, \
                mock.patch.object(main, "battery_info",
                                  return_value={"pct": 20, "mv": 3600, "charging": False}):
            main._maybe_edition()
            fetch.assert_not_called()
            main.battery_info.return_value = {"pct": 80, "mv": 3900, "charging": False}
            main._maybe_edition()                       # must not raise
        self.assertTrue(any("edition fetch failed" in m for m in logs))

    def test_fetched_on_completed_slot_before_ota(self):
        order = []
        from tests import test_wake_plan
        case = test_wake_plan.TestCycle("test_claim_before_render_and_complete_before_ota")
        case.setUp()
        try:
            with mock.patch.object(main, "_maybe_edition", side_effect=lambda: order.append("edition")):
                case.mocks[5].side_effect = lambda: order.append("ota")
                main.scheduled_cycle()
        finally:
            mock.patch.stopall()
        self.assertEqual(order, ["edition", "ota"])


if __name__ == "__main__":
    unittest.main()
