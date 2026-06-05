#!/usr/bin/env python3
"""
Magdeburg Smart City Hackathon — RAG source downloader.

Reads sources.yaml and writes everything into ./downloads/<category>/<id>.<ext>.

Modes:
  pdf       — plain HTTP GET, save as <id>.pdf
  html      — fetch HTML, render via trafilatura to clean text, save as <id>.txt
              (raw .html kept alongside for debugging)
  wikipedia — primary: MediaWiki API extracts; fallback: HTML + trafilatura

Install:  pip install requests trafilatura pyyaml
Run:      python download_pdfs.py
          python download_pdfs.py --only strategie,otto
          python download_pdfs.py --no-html        # only real PDFs
          python download_pdfs.py --retry-failed
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Please `pip install pyyaml` first.")

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("Please `pip install requests` first.")

try:
    import trafilatura  # type: ignore
except ImportError:
    trafilatura = None  # HTML extraction will fall back to raw .html only

HERE = Path(__file__).parent.resolve()
SOURCES_FILE = HERE / "sources.yaml"
OUT_ROOT = HERE / "downloads"
LOG_FILE = HERE / "download_log.json"

# Generic browser UA (used for magdeburg.de etc. so we look like Safari)
UA_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Wikipedia/WMF API etiquette: descriptive UA with contact info.
# See https://meta.wikimedia.org/wiki/User-Agent_policy
UA_WIKIPEDIA = (
    "MagdeburgSmartCityHackathon-RAG/1.0 "
    "(https://www.magdeburg.de/; contact: hackathon-organizers)"
)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/pdf;q=0.95,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
)


@dataclass
class Entry:
    category: str
    id: str
    title: str
    url: str
    format: str
    note: str = ""

    @property
    def referer(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}/"


def load_entries(path: Path = SOURCES_FILE) -> list[Entry]:
    data: dict[str, list[dict[str, Any]]] = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )
    out: list[Entry] = []
    for category, items in data.items():
        for it in items:
            out.append(
                Entry(
                    category=category,
                    id=it["id"],
                    title=it["title"],
                    url=it["url"],
                    format=it["format"],
                    note=it.get("note", "").strip(),
                )
            )
    return out


def http_get(
    url: str,
    *,
    user_agent: str = UA_BROWSER,
    referer: str | None = None,
    timeout: int = 30,
    max_retries: int = 4,
) -> requests.Response:
    """GET with proper UA, optional Referer, and retry/backoff on 429 + 5xx."""
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer

    backoff = 2.0
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = SESSION.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            # Retry on transient codes
            if r.status_code in (429, 500, 502, 503, 504):
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff
                time.sleep(min(wait, 30))
                backoff *= 2
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            time.sleep(backoff)
            backoff *= 2
        except requests.exceptions.HTTPError:
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Gave up after {max_retries} retries on {url}")


def fetch_pdf(entry: Entry, dest: Path) -> dict[str, Any]:
    r = http_get(entry.url, referer=entry.referer, timeout=60)
    ctype = r.headers.get("Content-Type", "").lower()
    if "pdf" not in ctype and not r.content[:4] == b"%PDF":
        snippet = r.text[:200].replace("\n", " ")
        if len(r.content) < 2048 and "<html" in r.text.lower():
            raise RuntimeError(f"Server returned HTML, not PDF (snippet: {snippet!r})")
    dest.write_bytes(r.content)
    return {"bytes": len(r.content), "content_type": ctype}


def fetch_html(entry: Entry, dest_html: Path, dest_txt: Path) -> dict[str, Any]:
    r = http_get(entry.url, timeout=30)
    dest_html.write_text(r.text, encoding="utf-8")
    extracted = ""
    if trafilatura is not None:
        extracted = (
            trafilatura.extract(
                r.text,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )
            or ""
        )
    if not extracted:
        extracted = "<no trafilatura installed or extraction empty — see .html file>"
    dest_txt.write_text(
        f"# {entry.title}\nSource: {entry.url}\n\n{extracted}\n", encoding="utf-8"
    )
    return {"bytes_html": len(r.content), "bytes_txt": len(extracted)}


def fetch_wikipedia(entry: Entry, dest: Path) -> dict[str, Any]:
    """Wikipedia: API extract first, fall back to HTML page if extract is empty."""
    parsed = urlparse(entry.url)
    if "/wiki/" not in parsed.path:
        raise RuntimeError("Not a /wiki/ URL")

    # Decode URL-encoded title first, THEN re-encode for the API call.
    # Without this, %C3%9F becomes %25C3%259F (double-encoding).
    title = unquote(parsed.path.split("/wiki/", 1)[1])

    api = (
        f"{parsed.scheme}://{parsed.netloc}/w/api.php"
        f"?action=query&prop=extracts&format=json"
        f"&redirects=1&explaintext=1&exsectionformat=plain"
        f"&titles={quote(title)}"
    )
    r = http_get(api, user_agent=UA_WIKIPEDIA, timeout=30)
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise RuntimeError("Wikipedia API returned no pages")
    page = next(iter(pages.values()))

    # If the API explicitly says the page is missing, fail fast — don't fall
    # back to HTML because /wiki/<missing-title> will just 404 too.
    if "missing" in page:
        raise RuntimeError(
            f"Wikipedia article '{title}' does not exist (check the title; "
            f"the API returned 'missing'). Fix the URL in sources.yaml."
        )

    extract = page.get("extract", "")
    resolved_title = page.get("title", title)

    # Fallback: empty extract → fetch the rendered HTML page and run trafilatura.
    # Happens on list-heavy or template-heavy pages where prop=extracts gives nothing.
    if not extract:
        html = http_get(
            f"{parsed.scheme}://{parsed.netloc}/wiki/{quote(title)}",
            user_agent=UA_WIKIPEDIA,
            timeout=30,
        ).text
        if trafilatura is not None:
            extract = (
                trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    favor_recall=True,
                )
                or ""
            )
        if not extract:
            raise RuntimeError(
                "Empty extract and HTML-fallback also empty"
                f" (install trafilatura?)"
            )

    dest.write_text(
        f"# {entry.title}\nSource: {entry.url}\n\n{extract}\n", encoding="utf-8"
    )
    return {"bytes": len(extract), "title": resolved_title}


def process(entry: Entry, retry_failed_only: bool, log: dict[str, Any]) -> dict[str, Any]:
    cat_dir = OUT_ROOT / entry.category
    cat_dir.mkdir(parents=True, exist_ok=True)

    key = f"{entry.category}/{entry.id}"
    prev = log.get(key, {})

    if entry.format == "pdf":
        dest = cat_dir / f"{entry.id}.pdf"
    elif entry.format in ("wikipedia", "html"):
        dest = cat_dir / f"{entry.id}.txt"
    else:
        return {**prev, "key": key, "status": "skip-unknown-format"}

    if dest.exists() and prev.get("status") == "ok" and not retry_failed_only:
        return {**prev, "key": key, "status": "cached"}

    if retry_failed_only and prev.get("status") == "ok":
        return {**prev, "key": key, "status": "cached"}

    try:
        if entry.format == "pdf":
            meta = fetch_pdf(entry, dest)
        elif entry.format == "wikipedia":
            meta = fetch_wikipedia(entry, dest)
        else:  # html
            html_dest = cat_dir / f"{entry.id}.html"
            meta = fetch_html(entry, html_dest, dest)
        return {
            "key": key,
            "status": "ok",
            "url": entry.url,
            "path": str(dest.relative_to(HERE)),
            "title": entry.title,
            **meta,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "key": key,
            "status": "error",
            "url": entry.url,
            "title": entry.title,
            "error": f"{type(e).__name__}: {e}",
        }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--only", help="Comma-separated list of categories to download")
    ap.add_argument("--no-html", action="store_true", help="Skip html/wikipedia entries")
    ap.add_argument("--no-pdf", action="store_true", help="Skip PDF entries")
    ap.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-attempt previously failed downloads (skip cached ok)",
    )
    ap.add_argument(
        "--sleep",
        type=float,
        default=0.6,
        help="Politeness delay between requests (Wikipedia gets 2x this).",
    )
    args = ap.parse_args()

    log: dict[str, Any] = {}
    if LOG_FILE.exists():
        try:
            log = {row["key"]: row for row in json.loads(LOG_FILE.read_text())}
        except Exception:  # noqa: BLE001
            log = {}

    entries = load_entries()
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        entries = [e for e in entries if e.category in wanted]
    if args.no_html:
        entries = [e for e in entries if e.format == "pdf"]
    if args.no_pdf:
        entries = [e for e in entries if e.format != "pdf"]

    results: list[dict[str, Any]] = []
    print(f"Processing {len(entries)} entries → {OUT_ROOT}")
    for i, e in enumerate(entries, 1):
        res = process(e, args.retry_failed, log)
        marker = {"ok": "✓", "cached": "·", "error": "✗"}.get(res["status"], "?")
        size = res.get("bytes") or res.get("bytes_txt") or 0
        size_str = f"{size/1024:>7.1f} KB" if size else "       —"
        print(
            f"  {marker} [{i:2}/{len(entries)}] "
            f"{e.category:11} {e.id:38} {size_str}  {res.get('error','')}"
        )
        results.append(res)
        log[res["key"]] = res
        # Be extra polite to Wikipedia (they explicitly rate-limit bots)
        time.sleep(args.sleep * (2 if e.format == "wikipedia" else 1))

    LOG_FILE.write_text(
        json.dumps(list(log.values()), indent=2, ensure_ascii=False)
    )

    ok = sum(1 for r in results if r["status"] in ("ok", "cached"))
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\nDone. ok/cached: {ok}   errors: {err}")
    print(f"Log: {LOG_FILE}")
    if err:
        print("\nErrors:")
        for r in results:
            if r["status"] == "error":
                print(f"  {r['key']}  {r.get('error')}")
                print(f"    URL: {r['url']}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
