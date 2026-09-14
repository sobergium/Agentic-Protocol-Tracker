from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan import event_for, generated_catalog, github_api_urls, normalize_content, restricted_observation
from scripts.validate_registry import validate


class UniversalRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = json.loads((ROOT/"registry/taxonomies.json").read_text())
        cls.entities = json.loads((ROOT/"registry/entities.json").read_text())["entities"]
        cls.sources = json.loads((ROOT/"registry/sources.json").read_text())["sources"]

    def test_registry_validates(self):
        self.assertEqual(validate(), [])

    def test_every_universal_domain_is_represented(self):
        observed = {domain for item in self.entities for domain in item["domains"]}
        self.assertEqual(observed, set(self.taxonomy["domains"]))

    def test_every_entity_has_source(self):
        self.assertEqual({item["entityId"] for item in self.sources}, {item["id"] for item in self.entities})

    def test_all_canonical_urls_are_https(self):
        self.assertTrue(all(item["canonicalUrl"].startswith("https://") for item in self.sources))

    def test_no_discovery_source_is_canonical_evidence(self):
        self.assertTrue(all(item["authority"] != "discovery" for item in self.sources))

    def test_ids_are_unique_within_registries(self):
        self.assertEqual(len({item["id"] for item in self.entities}), len(self.entities))
        self.assertEqual(len({item["id"] for item in self.sources}), len(self.sources))

    def test_expected_source_families_exist(self):
        types = {item["sourceType"] for item in self.sources}
        for expected in ["specification","github_repository","model_catalog","regulatory_publications","payment_network","research_api"]:
            self.assertIn(expected, types)

    def test_github_adapter_expands_machine_endpoints(self):
        urls = github_api_urls("https://github.com/coinbase/x402")
        self.assertEqual(len(urls), 3)
        self.assertIn("api.github.com/repos/coinbase/x402", urls[0])

    def test_json_hash_input_is_key_order_independent(self):
        left = normalize_content(b'{"b":2,"a":1}', "application/json")
        right = normalize_content(b'{"a":1,"b":2}', "application/json")
        self.assertEqual(left, right)

    def test_html_normalization_removes_dynamic_script_content(self):
        left = normalize_content(b'<main>Signal</main><script>nonce=1</script>', "text/html")
        right = normalize_content(b'<main>Signal</main><script>nonce=2</script>', "text/html")
        self.assertEqual(left, right)

    def test_restricted_primary_is_distinct_from_source_error(self):
        import urllib.error
        source = self.sources[0]
        exc = urllib.error.HTTPError(source["canonicalUrl"], 403, "Forbidden", {}, None)
        observation = restricted_observation(source, exc, "2026-01-01T00:00:00Z")
        self.assertEqual(observation["status"], "restricted")
        self.assertEqual(observation["responses"][0]["status"], 403)

    def test_event_is_provisional_and_evidenced(self):
        source = self.sources[0]
        new = {"contentHash":"a"*64,"responses":[{"url":source["canonicalUrl"],"status":200}]}
        event = event_for(source, None, new, "2026-01-01T00:00:00Z")
        self.assertEqual(event["publicationState"], "published_provisional")
        self.assertEqual(event["reviewStatus"], "unreviewed")
        self.assertEqual(event["evidence"]["canonicalUrl"], source["canonicalUrl"])

    def test_generated_catalog_covers_entities(self):
        catalog = generated_catalog(self.entities, self.sources, {})
        self.assertEqual(catalog["counts"]["entities"], len(self.entities))
        self.assertEqual(len(catalog["entities"]), len(self.entities))
        self.assertIn("restricted", catalog["counts"])


if __name__ == "__main__":
    unittest.main()
