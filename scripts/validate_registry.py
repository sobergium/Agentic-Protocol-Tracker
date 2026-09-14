from __future__ import annotations

import re
from urllib.parse import urlparse

from scripts.common import read_json

ID = re.compile(r"^[a-z0-9-]+$")


def validate() -> list[str]:
    taxonomy = read_json("registry/taxonomies.json")
    entities = read_json("registry/entities.json")["entities"]
    sources = read_json("registry/sources.json")["sources"]
    errors: list[str] = []
    entity_ids = [item.get("id") for item in entities]
    source_ids = [item.get("id") for item in sources]
    if len(entity_ids) != len(set(entity_ids)):
        errors.append("duplicate entity id")
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate source id")
    required_entity = {"id", "name", "type", "domains", "steward", "jurisdiction", "status"}
    required_source = {"id", "entityId", "authority", "sourceType", "canonicalUrl", "adapter", "cadence", "allowedClaims", "reviewStatus", "enabled"}
    entity_set = set(entity_ids)
    for entity in entities:
        missing = required_entity - entity.keys()
        if missing:
            errors.append(f"{entity.get('id')}: missing entity fields {sorted(missing)}")
        if not ID.fullmatch(entity.get("id", "")):
            errors.append(f"{entity.get('id')}: invalid entity id")
        if entity.get("type") not in taxonomy["entityTypes"]:
            errors.append(f"{entity.get('id')}: undefined entity type")
        for domain in entity.get("domains", []):
            if domain not in taxonomy["domains"]:
                errors.append(f"{entity.get('id')}: undefined domain {domain}")
    covered_entities: set[str] = set()
    for source in sources:
        missing = required_source - source.keys()
        if missing:
            errors.append(f"{source.get('id')}: missing source fields {sorted(missing)}")
        if not ID.fullmatch(source.get("id", "")):
            errors.append(f"{source.get('id')}: invalid source id")
        if source.get("entityId") not in entity_set:
            errors.append(f"{source.get('id')}: dangling entity reference")
        else:
            covered_entities.add(source["entityId"])
        for key, taxonomy_key in [("authority","sourceRoles"),("sourceType","sourceTypes"),("adapter","adapters"),("cadence","cadences"),("reviewStatus","reviewStatuses")]:
            if source.get(key) not in taxonomy[taxonomy_key]:
                errors.append(f"{source.get('id')}: undefined {key}")
        parsed = urlparse(source.get("canonicalUrl", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{source.get('id')}: canonical URL must be HTTPS")
        if not source.get("allowedClaims"):
            errors.append(f"{source.get('id')}: no allowed claim types")
    missing_sources = entity_set - covered_entities
    if missing_sources:
        errors.append(f"entities without canonical sources: {sorted(missing_sources)}")
    covered_domains = {domain for entity in entities if entity["id"] in covered_entities for domain in entity["domains"]}
    missing_domains = set(taxonomy["domains"]) - covered_domains
    if missing_domains:
        errors.append(f"uncovered universal domains: {sorted(missing_domains)}")
    return errors


def main() -> None:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    entities = read_json("registry/entities.json")["entities"]
    sources = read_json("registry/sources.json")["sources"]
    print(f"Registry valid: {len(entities)} entities, {len(sources)} canonical sources")


if __name__ == "__main__":
    main()
