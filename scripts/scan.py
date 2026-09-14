from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from typing import Any

from scripts.common import ROOT, content_hash, read_json, utc_now, write_json
from scripts.validate_registry import validate

MAX_BYTES = 5_000_000
USER_AGENT = "SystemsOverSignals-EvidenceEngine/0.1 (+https://github.com/sobergium/Agentic-Protocol-Tracker)"


def github_api_urls(url: str) -> list[str]:
    match = re.match(r"https://github\.com/([^/]+)/([^/#?]+)", url)
    if not match:
        return [url]
    owner, repository = match.groups()
    repository = repository.removesuffix(".git")
    base = f"https://api.github.com/repos/{owner}/{repository}"
    return [base, f"{base}/releases?per_page=10", f"{base}/tags?per_page=10"]


def fetch_url(url: str, token: str | None = None) -> tuple[bytes, dict[str, str], int]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json, application/json, text/html;q=0.9, */*;q=0.5"}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError(f"response exceeded {MAX_BYTES} bytes")
        metadata = {"contentType":response.headers.get("Content-Type",""),"etag":response.headers.get("ETag",""),"lastModified":response.headers.get("Last-Modified",""),"resolvedUrl":response.geturl()}
        return content, metadata, response.status


def observe(source: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    urls = github_api_urls(source["canonicalUrl"]) if source["adapter"] == "github" else [source["canonicalUrl"]]
    chunks, responses = [], []
    for url in urls:
        content, metadata, status = fetch_url(url, token)
        chunks.append(content)
        responses.append({"url":url,"status":status,**metadata})
    return {"sourceId":source["id"],"entityId":source["entityId"],"status":"ok","contentHash":content_hash(b"\n--SOURCE-BOUNDARY--\n".join(chunks)),"responses":responses}


def event_for(source: dict[str, Any], old: dict[str, Any] | None, new: dict[str, Any], observed_at: str) -> dict[str, Any]:
    seed = f"{source['id']}:{new['contentHash']}:{observed_at}".encode()
    return {"eventId":hashlib.sha256(seed).hexdigest()[:24],"sourceId":source["id"],"entityId":source["entityId"],"observedAt":observed_at,"publicationState":"published_provisional","oldHash":old.get("contentHash") if old else None,"newHash":new["contentHash"],"changeType":"baseline_observed" if old is None else "upstream_content_changed","evidence":{"canonicalUrl":source["canonicalUrl"],"authority":source["authority"],"adapter":source["adapter"],"httpResponses":new["responses"]},"reviewStatus":"unreviewed"}


def append_events(events: list[dict[str, Any]], date: str) -> None:
    if not events:
        return
    target = ROOT / "data" / "events" / f"{date}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if target.exists():
        existing_ids = {json.loads(line)["eventId"] for line in target.read_text().splitlines() if line.strip()}
    with target.open("a", encoding="utf-8") as handle:
        for event in events:
            if event["eventId"] not in existing_ids:
                handle.write(json.dumps(event, sort_keys=True) + "\n")


def generated_catalog(entities: list[dict[str, Any]], sources: list[dict[str, Any]], observations: dict[str, Any]) -> dict[str, Any]:
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        observation = observations.get(source["id"])
        by_entity.setdefault(source["entityId"], []).append({"sourceId":source["id"],"sourceType":source["sourceType"],"canonicalUrl":source["canonicalUrl"],"scanStatus":observation.get("status","not_scanned") if observation else "not_scanned","reviewStatus":source["reviewStatus"],"contentHash":observation.get("contentHash") if observation else None})
    rows = [{**entity,"sources":by_entity.get(entity["id"],[])} for entity in entities]
    domains = sorted({domain for entity in entities for domain in entity["domains"]})
    return {"registryVersion":"1.0.0","publicationState":"published_provisional","counts":{"entities":len(entities),"sources":len(sources),"domains":len(domains),"scanned":sum(1 for value in observations.values() if value.get("status")=="ok"),"errors":sum(1 for value in observations.values() if value.get("status")=="error")},"domains":domains,"entities":rows}


def run(selected: set[str] | None = None) -> tuple[int, int]:
    errors = validate()
    if errors:
        raise RuntimeError("registry invalid: " + "; ".join(errors))
    entities = read_json("registry/entities.json")["entities"]
    sources = [item for item in read_json("registry/sources.json")["sources"] if item["enabled"]]
    previous_document = read_json("data/snapshots/latest.json", {"observations":{}})
    previous = previous_document.get("observations", {})
    observations, events = dict(previous), []
    observed_at, token = utc_now(), os.environ.get("GITHUB_TOKEN")
    success = failure = 0
    for source in sources:
        if selected and source["id"] not in selected:
            continue
        old = previous.get(source["id"])
        try:
            new = observe(source, token)
            success += 1
            if old is None or old.get("contentHash") != new["contentHash"] or old.get("status") != "ok":
                new["observedAt"] = observed_at
                observations[source["id"]] = new
                events.append(event_for(source, old, new, observed_at))
        except Exception as exc:
            failure += 1
            error = {"sourceId":source["id"],"entityId":source["entityId"],"status":"error","errorType":type(exc).__name__,"error":str(exc)[:500]}
            if old is None or old.get("status") != "error" or old.get("error") != error["error"]:
                error["observedAt"] = observed_at
                observations[source["id"]] = error
    write_json("data/snapshots/latest.json", {"registryVersion":"1.0.0","observations":observations})
    append_events(events, observed_at[:10])
    write_json("site/generated/catalog.json", generated_catalog(entities, sources, observations))
    write_json("site/generated/latest-changes.json", {"events":events})
    print(json.dumps({"successful":success,"failed":failure,"newEvents":len(events)},indent=2))
    return success, failure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args()
    success, _ = run(set(args.source) or None)
    if success == 0:
        raise SystemExit("No source scan succeeded")


if __name__ == "__main__":
    main()
