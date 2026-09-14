from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from scripts.common import ROOT, read_json


def recent_events(days: int = 7) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events: list[dict] = []
    event_root = ROOT / "data" / "events"
    if not event_root.exists():
        return events
    for path in sorted(event_root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                observed = datetime.fromisoformat(event["observedAt"].replace("Z","+00:00"))
                if observed >= cutoff:
                    events.append(event)
    return events


def render() -> str:
    events = recent_events()
    snapshot = read_json("data/snapshots/latest.json", {"observations":{}})
    errors = [item for item in snapshot["observations"].values() if item.get("status")=="error"]
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=7)
    lines = [f"# Weekly evidence review: {start} → {today}","","> This queue is post-publication. Records remain visibly provisional until disposition is recorded.","","## Summary","",f"- Provisional change events: **{len(events)}**",f"- Sources currently reporting errors: **{len(errors)}**","","## Required dispositions","","For each item choose: confirm, correct, reject, deeper-research, or supersede.",""]
    if events:
        for event in events:
            lines += [f"- [ ] {event['eventId']} — **{event['entityId']}** / {event['changeType']}",f"  - Source: {event['evidence']['canonicalUrl']}",f"  - Observed: {event['observedAt']}",f"  - Hash: {event['newHash']}"]
    else:
        lines.append("- No new change events in this review period.")
    lines += ["","## Source errors",""]
    if errors:
        for item in errors:
            lines.append(f"- [ ] **{item['sourceId']}** — {item.get('errorType')}: {item.get('error')}")
    else:
        lines.append("- No active source errors.")
    lines += ["","## Review record","","- Reviewer:","- Completed at:","- Corrections committed:","- Deeper-research items opened:"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render(), end="")
