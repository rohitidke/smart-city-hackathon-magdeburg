from __future__ import annotations

from datetime import date, datetime, timedelta
from html import unescape
import re
import xml.etree.ElementTree as ET

import requests

from app.tools import register_tool

EVENTS_RSS_URL = "https://www.magdeburg.de/media/rss/Veranstaltungshinweise_MMKT.xml"
EVENTS_PAGE_URL = "https://www.magdeburg.de/veranstaltungen"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
COMMON_MAGDEBURG_VENUES = {
    "machwerk",
    "petriförder",
    "gesellschaftshaus",
    "puppentheater",
    "forum gestaltung",
    "getec-arena",
    "literaturhaus",
    "volkshochschule",
    "guericke-zentrum",
    "kunstmuseum",
    "elbauenpark",
    "stadtbibliothek",
    "klosterbergegarten",
    "nicolaikirche",
    "wissenschaftshafen",
    "leiterstraße",
    "leibnizstraße",
    "breiter weg",
    "einladen",
    "nachbars garten",
    "kulturkollektiv",
    "schleinufer",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def _extract_event_fields(description: str) -> dict:
    text = " ".join(unescape(description or "").split())
    meta_match = re.match(
        r"(?P<start>\d{2}\.\d{2}\.\d{4})"
        r"(?:\s+bis\s+(?P<end>\d{2}\.\d{2}\.\d{4}))?"
        r"(?:\s+von\s+(?P<from>\d{2}:\d{2})\s+bis\s+(?P<to>\d{2}:\d{2})\s+Uhr|\s+ab\s+(?P<from_only>\d{2}:\d{2})\s+Uhr)?"
        r"(?:\s+in\s+(?P<location>.*?))?"
        r"(?::\s*(?P<summary>.*))?$",
        text,
    )

    start_date = _parse_date(meta_match.group("start")) if meta_match else None
    end_date = _parse_date(meta_match.group("end")) if meta_match and meta_match.group("end") else start_date

    time_from = None
    time_to = None
    location = ""
    summary = text
    if meta_match:
        time_from = meta_match.group("from") or meta_match.group("from_only")
        time_to = meta_match.group("to")
        location = (meta_match.group("location") or "").strip()
        summary = (meta_match.group("summary") or "").strip() or text

    return {
        "start_date": start_date,
        "end_date": end_date or start_date,
        "time_from": time_from,
        "time_to": time_to,
        "location": location,
        "summary": summary,
    }


def _looks_like_magdeburg_event(title: str, description: str, location: str) -> bool:
    haystack = f"{title} {description} {location}".lower()
    if "magdeburg" in haystack:
        return True
    if re.search(r"\b391\d{2}\b", haystack):
        return True
    return any(venue in haystack for venue in COMMON_MAGDEBURG_VENUES)


def _fetch_events() -> list[dict]:
    response = requests.get(EVENTS_RSS_URL, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    events = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = item.findtext("description") or ""
        parsed = _extract_event_fields(description)
        if not parsed["start_date"]:
            continue
        if not _looks_like_magdeburg_event(title, description, parsed["location"]):
            continue
        events.append(
            {
                "title": unescape(title),
                "url": link,
                "description": unescape(description),
                **parsed,
            }
        )

    events.sort(key=lambda event: (event["start_date"], event["time_from"] or "99:99", event["title"].lower()))
    return events


def _matches_timeframe(event: dict, zeitraum: str, today: date) -> bool:
    start = event["start_date"]
    end = event["end_date"] or start

    if zeitraum == "heute":
        return start <= today <= end

    if zeitraum == "morgen":
        tomorrow = today + timedelta(days=1)
        return start <= tomorrow <= end

    if zeitraum == "wochenende":
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        sunday = saturday + timedelta(days=1)
        return start <= sunday and end >= saturday

    if zeitraum == "bald":
        return end >= today

    return True


def _matches_keyword(event: dict, suchbegriff: str) -> bool:
    if not suchbegriff:
        return True
    needle = suchbegriff.lower().strip()
    haystack = f"{event['title']} {event['description']} {event['location']}".lower()
    return needle in haystack


def _format_event_time(event: dict, language: str) -> str:
    date_label = event["start_date"].strftime("%d.%m.%Y")
    if event["end_date"] and event["end_date"] != event["start_date"]:
        date_label = f"{date_label} - {event['end_date'].strftime('%d.%m.%Y')}"

    if event["time_from"] and event["time_to"]:
        return f"{date_label}, {event['time_from']}-{event['time_to']}"
    if event["time_from"]:
        return f"{date_label}, {event['time_from']}"
    return date_label


def veranstaltungen(
    zeitraum: str = "heute",
    suchbegriff: str = "",
    limit: int = 5,
    sprache: str = "de",
) -> str:
    sprache = "en" if (sprache or "").lower().startswith("en") else "de"
    zeitraum = (zeitraum or "heute").lower()
    limit = max(1, min(limit or 5, 8))

    try:
        events = _fetch_events()
    except Exception as exc:
        if sprache == "en":
            return (
                "Live event data for Magdeburg could not be loaded right now. "
                f"Please try again later or check the official calendar: {EVENTS_PAGE_URL} "
                f"(technical detail: {exc})"
            )
        return (
            "Live-Veranstaltungsdaten für Magdeburg konnten gerade nicht geladen werden. "
            f"Bitte versuchen Sie es später erneut oder prüfen Sie den offiziellen Kalender: {EVENTS_PAGE_URL} "
            f"(technisches Detail: {exc})"
        )

    today = datetime.now().date()
    filtered = [
        event for event in events
        if _matches_timeframe(event, zeitraum, today) and _matches_keyword(event, suchbegriff)
    ]

    if zeitraum == "bald":
        filtered = [event for event in filtered if event["end_date"] >= today]

    filtered = filtered[:limit]

    timeframe_labels = {
        "de": {
            "heute": "heute",
            "morgen": "morgen",
            "wochenende": "an diesem Wochenende",
            "bald": "demnächst",
        },
        "en": {
            "heute": "today",
            "morgen": "tomorrow",
            "wochenende": "this weekend",
            "bald": "soon",
        },
    }

    if not filtered:
        if sprache == "en":
            return (
                f"I couldn't find any matching events in Magdeburg {timeframe_labels['en'].get(zeitraum, 'for that period')}. "
                f"Source checked: {EVENTS_PAGE_URL}"
            )
        return (
            f"Ich konnte keine passenden Veranstaltungen in Magdeburg {timeframe_labels['de'].get(zeitraum, 'für diesen Zeitraum')} finden. "
            f"Geprüfte Quelle: {EVENTS_PAGE_URL}"
        )

    heading = (
        f"Events in Magdeburg {timeframe_labels['en'].get(zeitraum, 'for that period')}:"
        if sprache == "en"
        else f"Veranstaltungen in Magdeburg {timeframe_labels['de'].get(zeitraum, 'für diesen Zeitraum')}:"
    )

    lines = [heading]
    for event in filtered:
        lines.append(f"- **{event['title']}**")
        lines.append(f"  {_format_event_time(event, sprache)}")
        if event["location"]:
            lines.append(
                f"  Location: {event['location']}"
                if sprache == "en"
                else f"  Ort: {event['location']}"
            )
        teaser = event["summary"][:220].strip()
        if teaser:
            if len(event["summary"]) > 220:
                teaser += "..."
            lines.append(f"  {teaser}")
        if event["url"]:
            lines.append(f"  URL: {event['url']}")

    lines.append(
        f"Source: official Magdeburg event calendar ({EVENTS_PAGE_URL})"
        if sprache == "en"
        else f"Quelle: offizieller Veranstaltungskalender Magdeburg ({EVENTS_PAGE_URL})"
    )
    return "\n".join(lines)


register_tool(
    name="veranstaltungen",
    description="Live event lookup for Magdeburg from the official event calendar RSS feed.",
    parameters={
        "type": "object",
        "properties": {
            "zeitraum": {
                "type": "string",
                "enum": ["heute", "morgen", "wochenende", "bald"],
                "description": "Today, tomorrow, this weekend, or upcoming events.",
            },
            "suchbegriff": {
                "type": "string",
                "description": "Optional keyword such as concert, family, museum, children, music, or market.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of events to return (1-8).",
            },
            "sprache": {
                "type": "string",
                "enum": ["de", "en"],
                "description": "Antwortsprache.",
            },
        },
        "required": [],
    },
    handler=veranstaltungen,
)
