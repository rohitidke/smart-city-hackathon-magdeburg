from __future__ import annotations

from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
import xml.etree.ElementTree as ET

import requests

from app.tools import register_tool

SEARCH_URL = "https://html.duckduckgo.com/html/"
EVENTS_RSS_URL = "https://www.magdeburg.de/media/rss/Veranstaltungshinweise_MMKT.xml"
EVENTS_PAGE_URL = "https://www.magdeburg.de/veranstaltungen"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
MAGDEBURG_HINTS = {
    "magdeburg",
    "ottostadt",
    "elbauenpark",
    "alter markt",
    "39104",
    "39106",
    "39108",
    "39110",
    "39112",
    "39114",
    "39116",
    "39118",
    "39120",
    "39122",
    "39124",
    "39126",
    "39128",
    "39130",
}
MAGDEBURG_DOMAINS = {
    "magdeburg.de",
    "magdeburg-tourist.de",
    "ottostadt.de",
    "mvbnet.de",
    "stadtbibliothek.magdeburg.de",
}
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
EVENT_QUERY_KEYWORDS = {
    "event", "events", "veranstaltung", "veranstaltungen", "concert", "konzert",
    "festival", "show", "market", "flohmarkt", "exhibition", "ausstellung",
    "what's on", "what is on",
}
PAST_EVENT_QUERY_KEYWORDS = {
    "last week", "past week", "yesterday", "gestern", "letzte woche",
    "letzten woche", "vorige woche", "previous week", "happened", "stattgefunden",
}


def _is_english(sprache: str) -> bool:
    return (sprache or "").lower().startswith("en")


def _normalize_result_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [])
        if target:
            return unquote(target[0])
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return " ".join(value.split())


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


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture_title = False
        self.capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        class_name = attr_map.get("class", "") or ""

        if tag == "a" and "result__a" in class_name:
            self._flush_current()
            self.current = {
                "title": "",
                "snippet": "",
                "url": _normalize_result_url(attr_map.get("href", "") or ""),
            }
            self.capture_title = True
            return

        if self.current and "result__snippet" in class_name:
            self.capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self.capture_title and tag == "a":
            self.capture_title = False
        if self.capture_snippet and tag in {"a", "div"}:
            self.capture_snippet = False

    def handle_data(self, data: str) -> None:
        if not self.current:
            return
        if self.capture_title:
            self.current["title"] += data
        elif self.capture_snippet:
            self.current["snippet"] += data

    def close(self) -> None:
        super().close()
        self._flush_current()

    def _flush_current(self) -> None:
        if not self.current:
            return
        title = " ".join(self.current["title"].split())
        snippet = " ".join(self.current["snippet"].split())
        if title and self.current["url"]:
            self.results.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": self.current["url"],
                }
            )
        self.current = None


def _build_query(frage: str) -> str:
    cleaned = " ".join((frage or "").split())
    if "magdeburg" not in cleaned.lower():
        cleaned = f"{cleaned} Magdeburg"
    return cleaned


def _looks_like_magdeburg_result(result: dict[str, str]) -> bool:
    haystack = f"{result['title']} {result['snippet']} {result['url']}".lower()
    if any(hint in haystack for hint in MAGDEBURG_HINTS):
        return True

    netloc = urlparse(result["url"]).netloc.lower()
    return any(domain in netloc for domain in MAGDEBURG_DOMAINS)


def _looks_like_magdeburg_event(title: str, description: str, location: str) -> bool:
    haystack = f"{title} {description} {location}".lower()
    if "magdeburg" in haystack:
        return True
    if re.search(r"\b391\d{2}\b", haystack):
        return True
    return any(venue in haystack for venue in COMMON_MAGDEBURG_VENUES)


def _is_event_query(frage: str) -> bool:
    lower_frage = (frage or "").lower()
    return any(keyword in lower_frage for keyword in EVENT_QUERY_KEYWORDS)


def _is_past_event_query(frage: str) -> bool:
    lower_frage = (frage or "").lower()
    return any(keyword in lower_frage for keyword in PAST_EVENT_QUERY_KEYWORDS)


def _event_timeframe(frage: str) -> str:
    lower_frage = (frage or "").lower()
    if "tomorrow" in lower_frage or "morgen" in lower_frage:
        return "morgen"
    if "weekend" in lower_frage or "wochenende" in lower_frage:
        return "wochenende"
    if "upcoming" in lower_frage or "demnächst" in lower_frage or "kommende" in lower_frage:
        return "bald"
    return "heute"


def _event_topic(frage: str) -> str:
    lower_frage = (frage or "").lower()
    topic_map = {
        "music": "music",
        "concert": "music",
        "konzert": "musik",
        "musik": "musik",
        "family": "family",
        "kids": "kinder",
        "children": "kinder",
        "kinder": "kinder",
        "market": "markt",
        "flohmarkt": "flohmarkt",
        "museum": "museum",
        "exhibition": "ausstellung",
        "ausstellung": "ausstellung",
        "sport": "sport",
    }
    for keyword, mapped in topic_map.items():
        if keyword in lower_frage:
            return mapped
    return ""


def _build_event_search_query(frage: str) -> str:
    base_query = _build_query(frage)
    if _is_past_event_query(frage):
        today = datetime.now().date()
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
        date_terms = " OR ".join(
            (start + timedelta(days=offset)).strftime("%d.%m.%Y")
            for offset in range((end - start).days + 1)
        )
        base_query = f"{base_query} ({date_terms})"
    return base_query


def _looks_like_event_result(result: dict[str, str]) -> bool:
    haystack = f"{result['title']} {result['snippet']} {result['url']}".lower()
    return (
        "/veranstaltungskalender/" in result["url"].lower()
        or "veranstaltungskalender" in haystack
        or "event" in haystack
        or "veranstaltung" in haystack
        or "konzert" in haystack
    )


def _fetch_page(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def _absolute_url(url: str, base_url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    return url


def _iso_to_display(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.strftime("%d.%m.%Y, %H:%M")


def _iso_to_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _extract_eventfinder_events(html: str, page_url: str, limit: int) -> list[dict[str, str]]:
    script_blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    events: list[dict[str, str]] = []
    venues: dict[str, str] = {}

    def visit(node: object) -> None:
        nonlocal events, venues
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return

        node_type = node.get("@type")
        if node_type == "EventVenue" and node.get("@id"):
            venues[str(node["@id"])] = str(node.get("name", "")).strip()
        if node_type == "Event":
            location = ""
            raw_location = node.get("location")
            if isinstance(raw_location, dict):
                if raw_location.get("@id"):
                    location = venues.get(str(raw_location["@id"]), "")
                location = location or str(raw_location.get("name", "")).strip()
            events.append(
                {
                    "title": str(node.get("name", "")).strip(),
                    "time": _iso_to_display(str(node.get("startDate", "")).strip()),
                    "date": _iso_to_date(str(node.get("startDate", "")).strip()),
                    "location": location,
                    "summary": str(node.get("description", "")).strip(),
                    "url": str(node.get("url", "")).strip() or page_url,
                }
            )

        for value in node.values():
            visit(value)

    for block in script_blocks:
        try:
            parsed = json.loads(unescape(block))
        except json.JSONDecodeError:
            continue
        visit(parsed)

    cleaned = []
    seen = set()
    for event in events:
        if not event["title"] or event["title"] in seen:
            continue
        seen.add(event["title"])
        cleaned.append(event)
        if len(cleaned) >= limit:
            break
    return cleaned


def _extract_magdeburg_calendar_events(html: str, page_url: str, limit: int) -> list[dict[str, str]]:
    pattern = re.compile(
        r'<a\s+href="(?P<url>[^"]+)"[^>]*title="(?P<title>[^"]+)"[^>]*>.*?'
        r'<h3 class="list-title">\s*(?P<title_text>.*?)\s*</h3>.*?'
        r'<time[^>]*>(?P<date_html>.*?)</time>.*?'
        r'Uhrzeit:\s*</span>(?P<time_html>.*?)&nbsp;Uhr.*?'
        r'Veranstaltungsort:\s*</span>\s*(?P<location>.*?)\s*<span class="sr-only">.*?'
        r'<p>\s*(?P<summary>.*?)\s*<span class="more">',
        flags=re.DOTALL | re.IGNORECASE,
    )

    events = []
    for match in pattern.finditer(html):
        title = _clean_html_text(match.group("title_text") or match.group("title"))
        if not title:
            continue
        date_text = _clean_html_text(match.group("date_html"))
        date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_text)
        events.append(
            {
                "title": title,
                "time": date_text + ", " + _clean_html_text(match.group("time_html")),
                "date": _parse_date(date_match.group(1)) if date_match else None,
                "location": _clean_html_text(match.group("location")),
                "summary": _clean_html_text(match.group("summary")),
                "url": _absolute_url(unescape(match.group("url")), page_url),
            }
        )
        if len(events) >= limit:
            break
    return events


def _extract_events_from_result_page(result: dict[str, str], limit: int) -> list[dict[str, str]]:
    url = result["url"]
    html = _fetch_page(url)
    lower_url = url.lower()
    if "eventfinder.de" in lower_url:
        return _extract_eventfinder_events(html, url, limit)
    if "magdeburg.de" in lower_url:
        return _extract_magdeburg_calendar_events(html, url, limit)
    return []


def _filter_events_for_query(events: list[dict[str, str]], frage: str) -> list[dict[str, str]]:
    today = datetime.now().date()
    lower_frage = (frage or "").lower()

    if _is_past_event_query(frage):
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
        return [event for event in events if event.get("date") and start <= event["date"] <= end]

    if "tomorrow" in lower_frage or "morgen" in lower_frage:
        target = today + timedelta(days=1)
        return [event for event in events if event.get("date") == target]

    if "weekend" in lower_frage or "wochenende" in lower_frage:
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        sunday = saturday + timedelta(days=1)
        return [event for event in events if event.get("date") and saturday <= event["date"] <= sunday]

    if "upcoming" in lower_frage or "demnächst" in lower_frage or "kommende" in lower_frage:
        return [event for event in events if not event.get("date") or event["date"] >= today]

    return [event for event in events if event.get("date") == today]


def _fetch_search_results(
    frage: str,
    limit: int = 5,
    query_override: str | None = None,
    event_only: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    query = query_override or _build_query(frage)
    response = requests.get(
        f"{SEARCH_URL}?q={quote_plus(query)}&kl=de-de",
        headers=REQUEST_HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    parser = _DuckDuckGoHTMLParser()
    parser.feed(response.text)
    parser.close()

    seen_urls: set[str] = set()
    filtered_results: list[dict[str, str]] = []
    for result in parser.results:
        result["title"] = _clean_html_text(result["title"])
        result["snippet"] = _clean_html_text(result["snippet"])
        if not result["url"] or result["url"] in seen_urls:
            continue
        if not _looks_like_magdeburg_result(result):
            continue
        if event_only and not _looks_like_event_result(result):
            continue
        seen_urls.add(result["url"])
        filtered_results.append(result)
        if len(filtered_results) >= limit:
            break

    return query, filtered_results


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


def _matches_event_topic(event: dict, suchbegriff: str) -> bool:
    if not suchbegriff:
        return True
    haystack = f"{event['title']} {event['summary']} {event['location']}".lower()
    return suchbegriff.lower().strip() in haystack


def _format_event_time(event: dict) -> str:
    date_label = event["start_date"].strftime("%d.%m.%Y")
    if event["end_date"] and event["end_date"] != event["start_date"]:
        date_label = f"{date_label} - {event['end_date'].strftime('%d.%m.%Y')}"
    if event["time_from"] and event["time_to"]:
        return f"{date_label}, {event['time_from']}-{event['time_to']}"
    if event["time_from"]:
        return f"{date_label}, {event['time_from']}"
    return date_label


def _format_events_from_official_source(frage: str, limit: int, sprache: str) -> str:
    zeitraum = _event_timeframe(frage)
    suchbegriff = _event_topic(frage)
    today = datetime.now().date()

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

    filtered = [
        event for event in events
        if _matches_timeframe(event, zeitraum, today) and _matches_event_topic(event, suchbegriff)
    ][:limit]

    labels = {
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
                f"I couldn't find any matching events in Magdeburg {labels['en'].get(zeitraum, 'for that period')}.\n"
                f"Source: official Magdeburg event calendar ({EVENTS_PAGE_URL})"
            )
        return (
            f"Ich konnte keine passenden Veranstaltungen in Magdeburg {labels['de'].get(zeitraum, 'für diesen Zeitraum')} finden.\n"
            f"Quelle: offizieller Veranstaltungskalender Magdeburg ({EVENTS_PAGE_URL})"
        )

    heading = (
        f"Events in Magdeburg {labels['en'].get(zeitraum, 'for that period')}:"
        if sprache == "en"
        else f"Veranstaltungen in Magdeburg {labels['de'].get(zeitraum, 'für diesen Zeitraum')}:"
    )
    lines = [heading]
    for event in filtered:
        lines.append(f"- **{event['title']}**")
        lines.append(f"  {_format_event_time(event)}")
        if event["location"]:
            lines.append(f"  {'Location' if sprache == 'en' else 'Ort'}: {event['location']}")
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


def _format_events_from_web_search(frage: str, limit: int, sprache: str) -> str:
    query = _build_event_search_query(frage)
    try:
        _, results = _fetch_search_results(
            frage,
            limit=limit,
            query_override=query,
            event_only=True,
        )
        if not results:
            _, results = _fetch_search_results(
                frage,
                limit=limit,
                query_override=query,
                event_only=False,
            )
    except Exception as exc:
        if sprache == "en":
            return (
                "Live web search for past Magdeburg events could not be loaded right now. "
                f"Technical detail: {exc}"
            )
        return (
            "Die Live-Websuche nach vergangenen Magdeburger Veranstaltungen konnte gerade nicht geladen werden. "
            f"Technisches Detail: {exc}"
        )

    if not results:
        if sprache == "en":
            return (
                f"I couldn't find specific Magdeburg event pages on the web for: {frage}\n"
                "Please try a more specific date range or event topic."
            )
        return (
            f"Ich konnte keine konkreten Magdeburger Veranstaltungsseiten im Web finden für: {frage}\n"
            "Bitte versuchen Sie es mit einem genaueren Zeitraum oder Thema."
        )

    for result in results:
        try:
            extracted_events = _extract_events_from_result_page(result, limit=limit)
        except Exception:
            extracted_events = []
        extracted_events = _filter_events_for_query(extracted_events, frage)
        if extracted_events:
            heading = (
                f"Events found in Magdeburg for: {frage}"
                if sprache == "en"
                else f"Gefundene Veranstaltungen in Magdeburg für: {frage}"
            )
            lines = [heading]
            for event in extracted_events[:limit]:
                lines.append(f"- **{event['title']}**")
                if event["time"]:
                    lines.append(f"  {'Time' if sprache == 'en' else 'Zeit'}: {event['time']}")
                if event["location"]:
                    lines.append(f"  {'Location' if sprache == 'en' else 'Ort'}: {event['location']}")
                if event["summary"]:
                    teaser = event["summary"][:220].strip()
                    if len(event["summary"]) > 220:
                        teaser += "..."
                    lines.append(f"  {teaser}")
            lines.append(
                f"Source page: {result['title']} ({result['url']})"
                if sprache == "en"
                else f"Quellseite: {result['title']} ({result['url']})"
            )
            return "\n".join(lines)

    heading = (
        f"Magdeburg event results from the web for: {frage}"
        if sprache == "en"
        else f"Magdeburger Veranstaltungs-Webergebnisse für: {frage}"
    )
    lines = [heading]
    for result in results:
        lines.append(f"- **{result['title']}**")
        if result["snippet"]:
            lines.append(f"  {result['snippet']}")
        lines.append(f"  URL: {result['url']}")
    lines.append(
        "Source: live Magdeburg-focused web search"
        if sprache == "en"
        else "Quelle: live Magdeburg-fokussierte Websuche"
    )
    return "\n".join(lines)


def web_suche_magdeburg(frage: str, limit: int = 5, sprache: str = "de") -> str:
    sprache = "en" if _is_english(sprache) else "de"
    limit = max(3, min(limit or 5, 8))

    if _is_event_query(frage):
        return _format_events_from_web_search(frage, limit=limit, sprache=sprache)

    try:
        query, results = _fetch_search_results(frage, limit=limit)
    except Exception as exc:
        if sprache == "en":
            return (
                "Live web search for Magdeburg could not be loaded right now. "
                f"Technical detail: {exc}"
            )
        return (
            "Die Live-Websuche für Magdeburg konnte gerade nicht geladen werden. "
            f"Technisches Detail: {exc}"
        )

    if not results:
        if sprache == "en":
            return (
                f"I couldn't find any reliable Magdeburg-specific web results for: {query}\n"
                "Please try a more specific Magdeburg query."
            )
        return (
            f"Ich konnte keine verlässlichen Magdeburg-spezifischen Webergebnisse finden für: {query}\n"
            "Bitte formulieren Sie die Magdeburg-Anfrage etwas genauer."
        )

    heading = (
        f"Magdeburg web results for: {query}"
        if sprache == "en"
        else f"Magdeburg-Webergebnisse für: {query}"
    )
    lines = [heading]
    for result in results:
        lines.append(f"- **{result['title']}**")
        if result["snippet"]:
            lines.append(f"  {result['snippet']}")
        lines.append(f"  URL: {result['url']}")

    lines.append(
        "Source: live Magdeburg-focused web search via DuckDuckGo"
        if sprache == "en"
        else "Quelle: live Magdeburg-fokussierte Websuche über DuckDuckGo"
    )
    return "\n".join(lines)


register_tool(
    name="web_suche_magdeburg",
    description="Live Magdeburg-only web search fallback for city questions not covered by dedicated tools.",
    parameters={
        "type": "object",
        "properties": {
            "frage": {
                "type": "string",
                "description": "The Magdeburg-specific user question to search for on the web.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of web results to return.",
            },
            "sprache": {
                "type": "string",
                "description": "Answer language: 'de' or 'en'.",
            },
        },
        "required": ["frage"],
    },
    handler=web_suche_magdeburg,
)
