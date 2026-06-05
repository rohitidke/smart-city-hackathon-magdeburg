# Magdeburg Smart City Hackathon — RAG-Quellen

> *English version:* [README.en.md](./README.en.md).

Curated PDF / HTML / Wikipedia-Quellen für den RAG-Kontext-Layer des
Hackathons. Insgesamt **54 Quellen** in 9 Kategorien. Die Liste ist in
`sources.yaml` maschinenlesbar und wird über `download_pdfs.py` in
`./downloads/<kategorie>/` materialisiert (PDFs als `.pdf`, Wikipedia und
HTML als bereinigter Plaintext `.txt`).

## Schnelleinstieg

```bash
pip install pyyaml requests trafilatura
python download_pdfs.py                       # alles
python download_pdfs.py --only strategie,otto # nur einzelne Kategorien
python download_pdfs.py --no-html             # nur echte PDFs
python download_pdfs.py --retry-failed        # nach Patches nochmal
```

Der Downloader legt ein `download_log.json` an, das pro Quelle Status,
Pfad und Fehlertext mitschreibt — gut für eine spätere CI/Refresh-Loop.

> **Hinweis fürs Embedding:** Wikipedia- und HTML-Quellen kommen schon als
> sauberer Plaintext heraus (über `trafilatura` bzw. die MediaWiki-API);
> die kannst Du direkt chunken. Die echten PDFs sollten vor dem Embedding
> noch durch eine PDF-Pipeline (pypdf / docling / pymupdf) — bei den
> grafiklastigen Broschüren ist ein Tabellen-/Boxen-Splitter sinnvoll.

---

## Kategorien

### 1. Magdeburg Strategie

| ID | Titel | Format |
|---|---|---|
| `isek_2030_plus` | Integriertes Stadtentwicklungskonzept ISEK 2030+ | PDF |
| `kulturstrategie_2030` | Kulturstrategie 2030 — Kultur mit allen (Webversion) | PDF |
| `tourismuskonzept_2030_landing` | Tourismuskonzept 2030 (198 Maßnahmen) | HTML |
| `smart_city_landingpage` | Smart City Magdeburg — städtische Übersicht | HTML |
| `lsa_digital_2030_md` | Sachsen-Anhalt Digital 2030 — Projekte Raum MD | PDF |
| `smart_cities_modellprojekte_merkblatt` | KfW Merkblatt Modellprojekte Smart Cities | PDF |

Das **ISEK 2030+** ist das wichtigste Dokument — strategischer Kompass der
Stadt bis 2030 mit Wohnungsmarkt, Mobilität, Demografie, Stadtteilanalysen.
Die Tourismus- und Kultur-Strategien decken die Soft-Themen ab; die zwei
Förderdokumente erklären den Förderkontext, in dem Smart-City-Projekte in
Magdeburg stattfinden.

### 2. Tourismus

| ID | Titel | Format |
|---|---|---|
| `visit_md_48h_fruehjahr` | 48-Stunden-Broschüre Magdeburg, Frühjahr 2026 | PDF |
| `md_barrierefrei_2011` | Barrierefreier Tourismus in Magdeburg | PDF |
| `touristcard_flyer` | Magdeburg TouristCard Flyer 2025 | PDF |
| `visit_md_landing` | visit-magdeburg.de — Hauptseite | HTML |
| `magdeburg_tourist_de` | magdeburg-tourist.de — Sehenswertes-Sektion | HTML |

Die 48-Stunden-Broschüre ist der frischste Reiseführer (Frühjahr 2026,
gerade erschienen, perfekter Snippet-Lieferant für Q&A). `visit-magdeburg.de`
ist der **neue offizielle** Auftritt — vom alten `magdeburg-tourist.de`
hätte ich nur die Sehenswertes-Sektion gezogen, der Rest ist veraltetes
Tx-Module-CMS.

### 3. Kultur

| ID | Titel | Format |
|---|---|---|
| `kulturstrategie_2030_dup` | Kulturstrategie 2030 (s.o.) | PDF |
| `dom_magdeburg_wiki` | Magdeburger Dom | Wikipedia |
| `theater_magdeburg` | Theater Magdeburg | Wikipedia |
| `gruene_zitadelle` | Grüne Zitadelle (Hundertwasserhaus) | Wikipedia |
| `kloster_unser_lieben_frauen` | Kloster Unser Lieben Frauen | Wikipedia |
| `kulturhistorisches_museum` | Kulturhistorisches Museum | Wikipedia |
| `magdeburger_moderne` | Magdeburger Moderne (Bruno Taut etc.) | Wikipedia |

Kerngewebe der Magdeburger Kulturlandschaft. Die Wikipedia-Artikel sind
gepflegt und ergeben gut chunkbare 5–15 KB Textblöcke. Wenn ein Team später
einen "Kultur-Chatbot" baut, ist das hier der Mindeststandard.

### 4. Wikipedia-Artikel

| ID | Titel | Format |
|---|---|---|
| `magdeburg_de` | Magdeburg (DE-Hauptartikel) | Wikipedia |
| `magdeburg_en` | Magdeburg (EN — für intl. Teams) | Wikipedia |
| `magdeburg_geschichte` | Geschichte Magdeburgs | Wikipedia |
| `ovgu` | Otto-von-Guericke-Universität | Wikipedia |
| `1_fc_magdeburg` | 1. FC Magdeburg | Wikipedia |
| `sc_magdeburg` | SC Magdeburg (Handball) | Wikipedia |
| `stadtteile_magdeburg` | Liste der Stadtteile | Wikipedia |
| `elbe_wikipedia` | Elbe | Wikipedia |
| `wasserstrassenkreuz` | Wasserstraßenkreuz Magdeburg | Wikipedia |
| `mvb` | Magdeburger Verkehrsbetriebe | Wikipedia |
| `marego` | marego (Regionalverkehr) | Wikipedia |

Die "Liste der Stadtteile" ist als Geo-RAG-Grundlage sehr wertvoll —
verknüpft mit Open-Data-Demografiezahlen wird daraus ein guter Stadtteil-
Vergleichsbot. Elbe + Wasserstraßenkreuz + MVB/marego sind komplementär zu
Pegel-, GTFS- und Verkehrsdaten aus dem Open-Data-Pool.

### 5. Historische Texte / Stadtarchiv

| ID | Titel | Format |
|---|---|---|
| `stadtarchiv_landing` | Stadtarchiv Magdeburg — Übersicht | HTML |
| `stadtarchiv_digitaler_lesesaal` | Stadtarchiv — Digitaler Lesesaal (PDF-Broschüre) | PDF |
| `urkundenbuch_md_archive` | Urkundenbuch der Stadt Magdeburg (Bd. 1) | HTML |
| `magdeburger_recht_wiki` | Magdeburger Recht | Wikipedia |
| `zerstoerung_md_1631` | Magdeburger Hochzeit (1631) | Wikipedia |
| `festung_magdeburg` | Festung Magdeburg | Wikipedia |
| `graphsearch_md` | Magdeburg — EPFL Concept Summary | HTML |

Das Urkundenbuch ist eine echte historische Quelle (Internet Archive,
volldigitalisiert, frei verfügbar). "Magdeburger Recht" ist als Stichwort
für jeden Hackathon-Pitch Gold wert.

### 6. Magdeburger Marketing Kongress und Tourismus GmbH (MMKT)

| ID | Titel | Format |
|---|---|---|
| `mmkt_homepage` | MMKT Homepage | HTML |
| `mmkt_mediadaten_landing` | MMKT Mediadaten / Beteiligungsmöglichkeiten | HTML |
| `mmkt_strategische_marketingplanung_docplayer` | Strategische Marketingplanung (Volltext) | HTML |

Das offizielle Mediadaten-PDF liegt hinter dem Anzeigenkundenformular —
deshalb ist die Landingpage drin und im Notfall die DocPlayer-Volltext-
Variante der strategischen Marketingplanung. **Wenn Du direkten Kontakt
zur MMKT hast (Hardy Puls, Frau Heyking-Götze):** ein "Mediadaten 2026 PDF"
für den Hackathon anfragen, das wäre die sauberste Quelle.

### 7. DATEs Stadtmagazin

| ID | Titel | Format |
|---|---|---|
| `dates_epaper_landing` | DATEs E-Paper-Archiv (seit 2015) | HTML |
| `dates_issuu_archive` | DATEs auf issuu | HTML |
| `dates_essen_trinken` | DATEs Essen & Trinken | HTML |

DATEs publiziert über die Metro-Publisher-Plattform und mirrort auf issuu.
Auf der Detailseite jeder Ausgabe (`/service/e-paper/dates-<monat>-<jahr>/`)
gibt es keinen direkten PDF-Link in den Snippets, die JPG-Mockups sind
sichtbar. **Praktischer Tipp:** entweder das aktuelle Heft als issuu-Frame
einbetten, oder per Skript die HTML-Detailseite scrapen und den Cover-
Caption-Text plus die im Heft verlinkten Artikel als RAG-Snippets nutzen.
DATEs hat als Stadtmagazin ohnehin den größten Wert *außerhalb* des
gedruckten Hefts — das Online-Verzeichnis und der Veranstaltungskalender
sind die nützlicheren Datenquellen.

> **Optional:** Für eine "echte" PDF-Reihe könntet Ihr fünf bis zehn
> issuu-PDFs händisch ziehen (issuu erlaubt das nach Login bei eigenen
> Dokumenten) und den DATEs-Verlag um eine Hackathon-Freigabe bitten.

### 8. Otto K. / Otto-Familie (Otto I., Otto von Guericke, Ottostadt)

| ID | Titel | Format |
|---|---|---|
| `otto_guericke_biografie_unifl` | Biographie Otto von Guericke (Uni Flensburg) | PDF |
| `otto_guericke_wiki_de` | Otto von Guericke (DE) | Wikipedia |
| `otto_guericke_wiki_en` | Otto von Guericke (EN) | Wikipedia |
| `otto_i_hre` | Otto I. (HRR) — "Otto der Große" | Wikipedia |
| `editha` | Editha (Königin) — Magdeburg als Witwengabe | Wikipedia |
| `ottostadt_marke` | Marke "Ottostadt Magdeburg" | Wikipedia |
| `ovg_zentrum_landing` | Otto-von-Guericke-Zentrum / Lukasklause | HTML |

Ich habe "Otto K." als die Marken-Familie *Ottostadt* gelesen — also
Otto I. (Kaiser), Otto von Guericke (Bürgermeister/Naturforscher) und die
abgeleitete Stadtmarke. Falls Du spezifisch jemand anders meintest
(Otto-K. wie Karl-Otto?), gerne nochmal sagen.

### 9. Restaurants

| ID | Titel | Format |
|---|---|---|
| `visit_md_kulinarik` | visit-magdeburg.de Kulinarik | HTML |
| `dates_restaurants` | DATEs Restaurants in Magdeburg | HTML |
| `dates_bars` | DATEs Bars, Pubs, Kneipen | HTML |
| `dates_sonntagsbaecker` | DATEs Sonntagsbäcker | HTML |
| `visit_md_top10` | Top 10 Sehenswürdigkeiten | HTML |

**Realistisch gibt es kaum echte Restaurant-PDFs**, dafür aber zwei
hervorragende strukturierte HTML-Quellen (offizielle Tourismus-Seite +
DATEs). Wenn ein Team einen Restaurant-Empfehlungs-Bot baut, fährt man
mit diesen besser als mit irgendeinem PDF.

---

## Was noch fehlt / wo Du ergänzen könntest

Diese Punkte sind technisch nicht trivial zu autom-scrapen, lohnen sich
aber inhaltlich sehr — am besten kurz beim Rechteinhaber anfragen:

- **MMKT Mediadaten 2026 als PDF** (Hardy Puls / Frau Heyking-Götze)
- **Gastgeberverzeichnis 2024/2025** und **Kongressbroschüre** der MMKT
  (auf magdeburg-tourist.de gibt es Bestellseiten, kein offener Download)
- **Bidbook "Force of Attraction"** (Kulturhauptstadt-Bewerbung 2025) —
  die finale Version war zeitweise als PDF auf magdeburg2025.de, die
  Domain ist aktuell nicht mehr direkt zu erreichen; bei der Stadt nachfragen
- **Magdeburger Statistik** Hefte (`Bevölkerung & Demografie`, jährlich) —
  liegen unter `magdeburg.de/PDF/...PDF` aber der Server liefert die URLs
  nur mit gültigem Cookie/Session aus; im Browser einmal manuell ziehen
- **DATEs**: 5–10 ausgewählte Hefte als PDF (Verlag bitten, das ist eine
  Kleinigkeit für die)
- **Volksstimme**-Archiv: lokale Tageszeitung, Pay­wall — wäre für News-
  Fragen Gold, aber lizenzrechtlich heikel für einen offenen Hackathon

## Wie diese Quellen in den RAG passen

Pipeline-Skizze für den lokalen Stack — Qdrant + `bge-m3` via Ollama. Eine
lauffähige Variante mit vorgebautem Snapshot steht in
[`HACKATHON_README.md`](./HACKATHON_README.md):

1. `python download_pdfs.py` → 54 Dateien in `downloads/`
2. PDF-Parsing: pypdf / pymupdf für Text, Tabula/Camelot für Tabellen
   (`isek_2030_plus` hat schöne Tabellen, die mit reinem Text-Extract
   massakriert werden)
3. Chunking 800–1200 Tokens, 100 Token Overlap, mit Metadaten:
   `category`, `id`, `title`, `url` aus `sources.yaml`
4. Embeddings: `bge-m3` über Ollama (`ollama pull bge-m3`) — 1024-dim,
   mehrsprachig, für die deutschen Texte wichtig
5. Vektorstore: Qdrant (lokal per `docker compose`; der mitgelieferte
   Snapshot wird beim ersten Start restauriert)
6. Retrieval: top-k=5 mit MMR, Filter auf `category` als
   Werkzeug-Tool, damit die Teams "nur Restaurants" oder "nur Strategie"
   abfragen können

Pro RAG-Hygiene: Quellen-Metadaten **immer** in der Antwort zurückgeben
(`{source: visit_md_48h_fruehjahr, url: ...}`), sonst sind die Pitches
am Freitagabend voller Halluzinationen.
