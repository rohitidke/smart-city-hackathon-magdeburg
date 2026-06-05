# Magdeburg Smart City Hackathon — RAG sources

> *Deutsche Fassung:* [README.md](./README.md).

Curated PDF / HTML / Wikipedia sources for the hackathon's RAG context
layer. A total of **54 sources** across 9 categories. The list is machine-readable
in `sources.yaml` and is materialized via `download_pdfs.py` into
`./downloads/<category>/` (PDFs as `.pdf`, Wikipedia and HTML as cleaned plain
text `.txt`).

## Quick start

```bash
pip install pyyaml requests trafilatura
python download_pdfs.py                       # everything
python download_pdfs.py --only strategie,otto # only specific categories
python download_pdfs.py --no-html             # real PDFs only
python download_pdfs.py --retry-failed        # retry after patches
```

The downloader writes a `download_log.json` that records status, path and error
text per source — handy for a later CI/refresh loop.

> **Embedding note:** Wikipedia and HTML sources already come out as clean plain
> text (via `trafilatura` resp. the MediaWiki API); you can chunk those directly.
> The real PDFs should go through a PDF pipeline (pypdf / docling / pymupdf) before
> embedding — for the graphics-heavy brochures a table/box splitter is advisable.

---

## Categories

### 1. Magdeburg strategy

| ID | Title | Format |
|---|---|---|
| `isek_2030_plus` | Integrated Urban Development Concept ISEK 2030+ | PDF |
| `kulturstrategie_2030` | Cultural Strategy 2030 — Culture with Everyone (web version) | PDF |
| `tourismuskonzept_2030_landing` | Tourism Concept 2030 (198 measures) | HTML |
| `smart_city_landingpage` | Smart City Magdeburg — municipal overview | HTML |
| `lsa_digital_2030_md` | Saxony-Anhalt Digital 2030 — projects in the MD area | PDF |
| `smart_cities_modellprojekte_merkblatt` | KfW leaflet Model Projects Smart Cities | PDF |

**ISEK 2030+** is the most important document — the city's strategic compass to
2030 covering the housing market, mobility, demographics, district analyses. The
tourism and culture strategies cover the soft topics; the two funding documents
explain the funding context in which Smart City projects take place in Magdeburg.

### 2. Tourism

| ID | Title | Format |
|---|---|---|
| `visit_md_48h_fruehjahr` | 48-hour brochure Magdeburg, spring 2026 | PDF |
| `md_barrierefrei_2011` | Accessible tourism in Magdeburg | PDF |
| `touristcard_flyer` | Magdeburg TouristCard flyer 2025 | PDF |
| `visit_md_landing` | visit-magdeburg.de — main page | HTML |
| `magdeburg_tourist_de` | magdeburg-tourist.de — sights section | HTML |

The 48-hour brochure is the freshest travel guide (spring 2026, just published, a
perfect snippet source for Q&A). `visit-magdeburg.de` is the **new official**
presence — from the old `magdeburg-tourist.de` I'd have pulled only the sights
section, the rest is outdated Tx-Module CMS.

### 3. Culture

| ID | Title | Format |
|---|---|---|
| `kulturstrategie_2030_dup` | Cultural Strategy 2030 (see above) | PDF |
| `dom_magdeburg_wiki` | Magdeburg Cathedral | Wikipedia |
| `theater_magdeburg` | Theater Magdeburg | Wikipedia |
| `gruene_zitadelle` | Green Citadel (Hundertwasser house) | Wikipedia |
| `kloster_unser_lieben_frauen` | Monastery of Our Lady | Wikipedia |
| `kulturhistorisches_museum` | Museum of Cultural History | Wikipedia |
| `magdeburger_moderne` | Magdeburg Modernism (Bruno Taut etc.) | Wikipedia |

The core fabric of Magdeburg's cultural landscape. The Wikipedia articles are
well-maintained and yield nicely chunkable 5–15 KB text blocks. If a team later
builds a "culture chatbot", this is the minimum standard.

### 4. Wikipedia articles

| ID | Title | Format |
|---|---|---|
| `magdeburg_de` | Magdeburg (DE main article) | Wikipedia |
| `magdeburg_en` | Magdeburg (EN — for international teams) | Wikipedia |
| `magdeburg_geschichte` | History of Magdeburg | Wikipedia |
| `ovgu` | Otto von Guericke University | Wikipedia |
| `1_fc_magdeburg` | 1. FC Magdeburg | Wikipedia |
| `sc_magdeburg` | SC Magdeburg (handball) | Wikipedia |
| `stadtteile_magdeburg` | List of city districts | Wikipedia |
| `elbe_wikipedia` | Elbe | Wikipedia |
| `wasserstrassenkreuz` | Magdeburg Water Bridge / waterway junction | Wikipedia |
| `mvb` | Magdeburg transport company (MVB) | Wikipedia |
| `marego` | marego (regional transit) | Wikipedia |

The "list of city districts" is very valuable as a geo-RAG basis — combined with
open-data demographics it makes a good district-comparison bot. Elbe + waterway
junction + MVB/marego are complementary to level, GTFS and traffic data from the
open-data pool.

### 5. Historical texts / city archive

| ID | Title | Format |
|---|---|---|
| `stadtarchiv_landing` | Magdeburg City Archive — overview | HTML |
| `stadtarchiv_digitaler_lesesaal` | City Archive — Digital Reading Room (PDF brochure) | PDF |
| `urkundenbuch_md_archive` | Charter book of the City of Magdeburg (vol. 1) | HTML |
| `magdeburger_recht_wiki` | Magdeburg Law | Wikipedia |
| `zerstoerung_md_1631` | Sack of Magdeburg (1631) | Wikipedia |
| `festung_magdeburg` | Fortress Magdeburg | Wikipedia |
| `graphsearch_md` | Magdeburg — EPFL concept summary | HTML |

The charter book is a genuine historical source (Internet Archive, fully
digitized, freely available). "Magdeburg Law" as a keyword is gold for any
hackathon pitch.

### 6. Magdeburg Marketing Congress and Tourism GmbH (MMKT)

| ID | Title | Format |
|---|---|---|
| `mmkt_homepage` | MMKT homepage | HTML |
| `mmkt_mediadaten_landing` | MMKT media data / participation options | HTML |
| `mmkt_strategische_marketingplanung_docplayer` | Strategic marketing planning (full text) | HTML |

The official media-data PDF sits behind the advertiser form — so the landing page
is included and, as a fallback, the DocPlayer full-text variant of the strategic
marketing planning. **If you have direct contact with MMKT (Hardy Puls, Ms.
Heyking-Götze):** request a "Media Data 2026 PDF" for the hackathon, that would be
the cleanest source.

### 7. DATEs city magazine

| ID | Title | Format |
|---|---|---|
| `dates_epaper_landing` | DATEs e-paper archive (since 2015) | HTML |
| `dates_issuu_archive` | DATEs on issuu | HTML |
| `dates_essen_trinken` | DATEs Food & Drink | HTML |

DATEs publishes via the Metro Publisher platform and mirrors to issuu. On each
issue's detail page (`/service/e-paper/dates-<month>-<year>/`) there's no direct
PDF link in the snippets, the JPG mockups are visible. **Practical tip:** either
embed the current issue as an issuu frame, or script-scrape the HTML detail page
and use the cover caption text plus the articles linked in the issue as RAG
snippets. As a city magazine DATEs has its biggest value *outside* the printed
issue anyway — the online directory and the events calendar are the more useful
data sources.

> **Optional:** for a "real" PDF series you could manually pull five to ten issuu
> PDFs (issuu allows this after login for your own documents) and ask the DATEs
> publisher for a hackathon clearance.

### 8. Otto K. / Otto family (Otto I., Otto von Guericke, Ottostadt)

| ID | Title | Format |
|---|---|---|
| `otto_guericke_biografie_unifl` | Biography of Otto von Guericke (Uni Flensburg) | PDF |
| `otto_guericke_wiki_de` | Otto von Guericke (DE) | Wikipedia |
| `otto_guericke_wiki_en` | Otto von Guericke (EN) | Wikipedia |
| `otto_i_hre` | Otto I (HRE) — "Otto the Great" | Wikipedia |
| `editha` | Eadgyth (queen) — Magdeburg as a dower | Wikipedia |
| `ottostadt_marke` | The "Ottostadt Magdeburg" brand | Wikipedia |
| `ovg_zentrum_landing` | Otto von Guericke Centre / Lukasklause | HTML |

I read "Otto K." as the *Ottostadt* brand family — i.e. Otto I (emperor), Otto von
Guericke (mayor/natural scientist) and the derived city brand. If you specifically
meant someone else (Otto-K. as in Karl-Otto?), just let me know.

### 9. Restaurants

| ID | Title | Format |
|---|---|---|
| `visit_md_kulinarik` | visit-magdeburg.de cuisine | HTML |
| `dates_restaurants` | DATEs restaurants in Magdeburg | HTML |
| `dates_bars` | DATEs bars, pubs | HTML |
| `dates_sonntagsbaecker` | DATEs Sunday bakers | HTML |
| `visit_md_top10` | Top 10 sights | HTML |

**Realistically there are hardly any real restaurant PDFs**, but two excellent
structured HTML sources (the official tourism site + DATEs). If a team builds a
restaurant recommendation bot, these beat any PDF.

---

## What's still missing / where you could add

These items are not trivially auto-scrapeable but are very valuable in terms of
content — best to ask the rights holder briefly:

- **MMKT Media Data 2026 as PDF** (Hardy Puls / Ms. Heyking-Götze)
- **Host directory 2024/2025** and the MMKT **congress brochure** (magdeburg-tourist.de
  has order pages, no open download)
- **Bidbook "Force of Attraction"** (Capital of Culture bid 2025) — the final
  version was temporarily a PDF on magdeburg2025.de; the domain is currently not
  directly reachable; ask the city
- **Magdeburg statistics** booklets (`Population & demographics`, annual) — they
  live under `magdeburg.de/PDF/...PDF` but the server only serves the URLs with a
  valid cookie/session; pull once manually in the browser
- **DATEs**: 5–10 selected issues as PDF (ask the publisher, it's a trivial matter
  for them)
- **Volksstimme** archive: the local daily newspaper, paywalled — would be gold for
  news questions, but licensing-wise tricky for an open hackathon

## How these sources fit into the RAG

Pipeline sketch for the local stack — Qdrant + `bge-m3` via Ollama. A
ready-to-run variant with a prebuilt snapshot is in
[`HACKATHON_README.md`](./HACKATHON_README.md):

1. `python download_pdfs.py` → 54 files in `downloads/`
2. PDF parsing: pypdf / pymupdf for text, Tabula/Camelot for tables
   (`isek_2030_plus` has nice tables that get massacred by plain text extraction)
3. Chunking 800–1200 tokens, 100 token overlap, with metadata:
   `category`, `id`, `title`, `url` from `sources.yaml`
4. Embeddings: `bge-m3` via Ollama (`ollama pull bge-m3`) — 1024-dim,
   multilingual, important for the German texts
5. Vector store: Qdrant (local via `docker compose`; the bundled snapshot is
   restored on first start)
6. Retrieval: top-k=5 with MMR, filter on `category` as a tool so teams can query
   "restaurants only" or "strategy only"

For RAG hygiene: **always** return source metadata in the answer
(`{source: visit_md_48h_fruehjahr, url: ...}`), otherwise the Friday-evening
pitches are full of hallucinations.
