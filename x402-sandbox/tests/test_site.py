from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.styles = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.styles.append(values.get("href"))


class PortfolioSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (SITE / "index.html").read_text()
        cls.css = (SITE / "styles.css").read_text()
        cls.js = (SITE / "app.js").read_text()
        cls.parser = Markup()
        cls.parser.feed(cls.html)

    def test_static_entrypoint_and_assets_exist(self):
        for path in ["index.html","styles.css","app.js","assets/sos-mark.svg"]:
            self.assertTrue((SITE / path).is_file(), path)

    def test_navigation_targets_are_present(self):
        for target in ["tracker","sandbox","evidence","comparison"]:
            self.assertIn(target, self.parser.ids)

    def test_tracker_uses_generated_primary_source_catalog(self):
        self.assertIn("generated/catalog.json", self.js)
        for target in ["tracker-search", "domain-filter", "type-filter", "status-filter", "tracker-results"]:
            self.assertIn(target, self.parser.ids)

    def test_runtime_assets_are_local(self):
        self.assertEqual(self.parser.scripts, ["app.js"])
        self.assertEqual(self.parser.styles, ["styles.css"])
        self.assertNotIn("https://cdn", self.html)

    def test_all_three_models_and_failures_are_exposed(self):
        for value in ["authorization","upfront","escrow","replay","settlement","finality"]:
            self.assertIn(value, self.html + self.js)

    def test_simulation_boundary_is_visible(self):
        self.assertGreaterEqual(self.html.lower().count("simulat"), 3)
        self.assertIn("no wallet", self.html.lower())

    def test_brand_palette_is_defined(self):
        for token in ["--ivory","--ink","--teal"]:
            self.assertIn(token, self.css)


if __name__ == "__main__":
    unittest.main()
