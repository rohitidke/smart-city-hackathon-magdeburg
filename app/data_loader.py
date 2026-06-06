import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

trees_data: list[dict] = []
accidents_data: list[dict] = []
climate_monthly: list[dict] = []
tax_revenue: list[dict] = []
tax_columns: list[dict] = []
mietspiegel_baualter: list[dict] = []
mietspiegel_wohnflaeche: list[dict] = []
transit_stops: list[dict] = []
cafes_geojson: dict = {}
districts_geojson: dict = {}
zensus_pop: list[dict] = []
zensus_rent: list[dict] = []


def load_all():
    _load_trees()
    _load_accidents()
    _load_climate()
    _load_tax()
    _load_mietspiegel()
    _load_transit()
    _load_cafes()
    _load_districts()
    _load_zensus()


def _load_trees():
    global trees_data
    path = DATA_DIR / "Baumkataster" / "Baumkataster.geojson"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for feature in data.get("features", []):
        props = feature["properties"]
        coords = feature.get("geometry", {}).get("coordinates", [])
        trees_data.append({
            "stadtteil": props.get("Stadtteil", ""),
            "gattungsgruppe": props.get("Gattungsgruppe", ""),
            "gattung": props.get("Gattung", ""),
            "stammumfang": props.get("Stammumfang"),
            "baumhoehe": props.get("Baumhöhe"),
            "kronendurchmesser": props.get("Kronendurchmesser"),
            "pflanzjahr": props.get("Pflanzjahr"),
            "lon": coords[0] if len(coords) >= 2 else None,
            "lat": coords[1] if len(coords) >= 2 else None,
        })


def _load_accidents():
    global accidents_data
    path = DATA_DIR / "Unfaelle" / "Magdeburg_Unfallatlas.geojson"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for feature in data.get("features", []):
        props = feature["properties"]
        accidents_data.append({
            "jahr": int(props.get("UJAHR", 0)),
            "monat": props.get("UMONAT", ""),
            "stunde": props.get("USTUNDE", ""),
            "wochentag": int(props.get("UWOCHENTAG", 0)),
            "kategorie": int(props.get("UKATEGORIE", 0)),
            "art": int(props.get("UART", 0)),
            "licht": int(props.get("ULICHTVERH", 0)),
            "ist_rad": int(props.get("IstRad", 0)),
            "ist_pkw": int(props.get("IstPKW", 0)),
            "ist_fuss": int(props.get("IstFuss", 0)),
            "ist_krad": int(props.get("IstKrad", 0)),
            "lon": props.get("lon"),
            "lat": props.get("lat"),
        })


def _load_climate():
    global climate_monthly
    path = DATA_DIR / "sensor-data" / "json" / "klima-monat.json"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    climate_monthly = data.get("rows", [])


def _load_tax():
    global tax_revenue, tax_columns
    path = DATA_DIR / "steuereinnahmen" / "json" / "steuereinnahmen-2010-2025.json"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    tax_columns = data.get("columns", [])
    tax_revenue = data.get("rows", [])


def _load_mietspiegel():
    global mietspiegel_baualter, mietspiegel_wohnflaeche
    path1 = DATA_DIR / "mietspiegel-2024" / "nach-baualter.json"
    path2 = DATA_DIR / "mietspiegel-2024" / "nach-wohnflaeche.json"
    if path1.exists():
        with open(path1, encoding="utf-8") as f:
            mietspiegel_baualter = json.load(f).get("rows", [])
    if path2.exists():
        with open(path2, encoding="utf-8") as f:
            mietspiegel_wohnflaeche = json.load(f).get("rows", [])


def _load_transit():
    global transit_stops
    base = DATA_DIR / "OEV-Daten_NASA_GmbH" / "Haltestellen"
    if not base.exists():
        return
    type_map = {"ST": "Straßenbahn", "Taktbus": "Bus", "PlusBus": "PlusBus"}
    for subdir, typ in type_map.items():
        folder = base / subdir
        if not folder.exists():
            continue
        for csv_file in folder.glob("*.csv"):
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    ags = row.get("AGS Gemeinde", row.get("Referenzhaltestelle Gemeinde AGS", ""))
                    if "15003" not in str(ags):
                        continue
                    name = row.get("Haltestelle Name", row.get("Referenzhaltestelle Name", ""))
                    x = row.get("X-Koordinate", row.get("Referenzhaltestelle X-Koord.", ""))
                    y = row.get("Y-Koordinate", row.get("Referenzhaltestelle Y-Koord.", ""))
                    try:
                        lon = float(x.replace(",", ".")) if x else None
                        lat = float(y.replace(",", ".")) if y else None
                    except ValueError:
                        lon = lat = None
                    transit_stops.append({
                        "name": name,
                        "typ": typ,
                        "lon": lon,
                        "lat": lat,
                    })
    seen = set()
    unique = []
    for s in transit_stops:
        key = (s["name"], s["typ"])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    transit_stops = unique


def _load_cafes():
    global cafes_geojson
    path = DATA_DIR / "CafesOSM" / "CafesOSM.geojson"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        cafes_geojson = json.load(f)


def _load_districts():
    global districts_geojson
    path = DATA_DIR / "Stadtteile" / "Stadtteile.geojson"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        districts_geojson = json.load(f)


def _load_zensus():
    global zensus_pop, zensus_rent
    pop_path = DATA_DIR / "Zensus" / "ZensusBev.geojson"
    rent_path = DATA_DIR / "Zensus" / "ZensusMiete.geojson"
    if pop_path.exists():
        with open(pop_path, encoding="utf-8") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            props = feature["properties"]
            if props.get("Einwohner"):
                zensus_pop.append({
                    "einwohner": props["Einwohner"],
                })
    if rent_path.exists():
        with open(rent_path, encoding="utf-8") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            props = feature["properties"]
            zensus_rent.append({
                "miete_qm": props.get("nettokaltmiete_qm"),
                "wohnungen": props.get("wohnungen_miete_n"),
            })
