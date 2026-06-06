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

# KISS-MD data
kiss_population_monthly: list[dict] = []
kiss_apprentices: list[dict] = []
kiss_gdp: list[dict] = []
kiss_students: list[dict] = []
kiss_library_visits: list[dict] = []
kiss_public_transport: list[dict] = []
kiss_vehicle_fleet: list[dict] = []

# KISS-MD Demographics data
kiss_pop_age_gender: list[dict] = []
kiss_pop_age_groups: list[dict] = []
kiss_pop_dependency_ratios: list[dict] = []
kiss_pop_foreign: list[dict] = []
kiss_pop_migration: list[dict] = []
kiss_pop_districts: list[dict] = []

# KISS-MD Labor Market data
kiss_employment: list[dict] = []

# KISS-MD Health & Social data
kiss_doctors_pharmacies: list[dict] = []
kiss_rescue_services: list[dict] = []

# KISS-MD Construction & Housing data
kiss_construction_completions: list[dict] = []

# KISS-MD Education & Culture data (Phase 2)
kiss_schools: list[dict] = []

# KISS-MD Tourism & Recreation data (Phase 2)
kiss_tourism_arrivals: list[dict] = []
kiss_tourism_nights: list[dict] = []

# Stabstelle Klima data
climate_energy_emissions: list[dict] = []
climate_led_streetlights: dict = {}
climate_solar_energy: dict = {}


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
    _load_kiss_md()
    _load_stabstelle_klima()


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


def _load_kiss_md():
    """Load KISS-MD datasets."""
    global kiss_population_monthly, kiss_apprentices, kiss_gdp
    global kiss_students, kiss_library_visits, kiss_public_transport, kiss_vehicle_fleet
    global kiss_pop_age_gender, kiss_pop_age_groups, kiss_pop_dependency_ratios
    global kiss_pop_foreign, kiss_pop_migration, kiss_pop_districts
    global kiss_employment, kiss_doctors_pharmacies, kiss_rescue_services
    global kiss_construction_completions
    global kiss_schools, kiss_tourism_arrivals, kiss_tourism_nights

    kiss_dir = DATA_DIR / "kiss-md" / "json"

    # Population - monthly data
    pop_path = kiss_dir / "bevoelkerung" / "bevoelkerungsbestand-monatlich.json"
    if pop_path.exists():
        with open(pop_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_population_monthly = data.get("rows", [])

    # Labor market - apprentices
    apprentice_path = kiss_dir / "arbeitsmarkt" / "auszubildende-am-arbeitsort-nach-geschlecht.json"
    if apprentice_path.exists():
        with open(apprentice_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_apprentices = data.get("rows", [])

    # Economy - GDP
    gdp_path = kiss_dir / "wirtschaft" / "bruttoinlandsprodukt-und-bruttowertschoepfung.json"
    if gdp_path.exists():
        with open(gdp_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_gdp = data.get("rows", [])

    # Education - students (use the summary file with recent data)
    students_path = kiss_dir / "bildung-und-kultur" / "studierende-an-den-hochschulen-im-wintersemester.json"
    if students_path.exists():
        with open(students_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_students = data.get("rows", [])

    # Culture - library visits
    library_path = kiss_dir / "bildung-und-kultur" / "besuche-nach-bibliotheksart.json"
    if library_path.exists():
        with open(library_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_library_visits = data.get("rows", [])

    # Transport - public transit passengers
    transit_path = kiss_dir / "verkehr" / "befoerderte-personen-der-magdeburger-verkehrsbetriebe-gmbh-und-co-kg.json"
    if transit_path.exists():
        with open(transit_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_public_transport = data.get("rows", [])

    # Transport - vehicle fleet
    vehicle_path = kiss_dir / "verkehr" / "entwicklung-des-kraftfahrzeugbestandes-in-magdeburg.json"
    if vehicle_path.exists():
        with open(vehicle_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_vehicle_fleet = data.get("rows", [])

    # Demographics - age and gender
    age_gender_path = kiss_dir / "bevoelkerung" / "bevoelkerung-mit-hauptwohnsitz-nach-alter-und-geschlecht.json"
    if age_gender_path.exists():
        with open(age_gender_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_age_gender = data.get("rows", [])

    # Demographics - age groups
    age_groups_path = kiss_dir / "bevoelkerung" / "entwicklung-der-hauptwohnsitzbevoelkerung-nach-altersgruppen.json"
    if age_groups_path.exists():
        with open(age_groups_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_age_groups = data.get("rows", [])

    # Demographics - dependency ratios
    dependency_path = kiss_dir / "bevoelkerung" / "jugend-und-altenquote-der-hauptwohnsitzbevoelkerung.json"
    if dependency_path.exists():
        with open(dependency_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_dependency_ratios = data.get("rows", [])

    # Demographics - foreign residents
    foreign_path = kiss_dir / "bevoelkerung" / "entwicklung-der-auslaendischen-hauptwohnsitzbevoelkerung.json"
    if foreign_path.exists():
        with open(foreign_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_foreign = data.get("rows", [])

    # Demographics - migration
    migration_path = kiss_dir / "bevoelkerung" / "wanderungssaldo-nach-altersgruppen.json"
    if migration_path.exists():
        with open(migration_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_migration = data.get("rows", [])

    # Demographics - districts
    districts_path = kiss_dir / "bevoelkerung" / "hauptwohnsitzbevoelkerung-nach-statistischen-bezirken-und-geschlecht.json"
    if districts_path.exists():
        with open(districts_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_pop_districts = data.get("rows", [])

    # Labor Market - employment
    employment_path = kiss_dir / "arbeitsmarkt" / "sozialversicherungspflichtig-beschaeftigte-am-arbeitsort-nach-geschlecht-altersklassen-und-staatsangehoerigkeit.json"
    if employment_path.exists():
        with open(employment_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_employment = data.get("rows", [])

    # Health & Social - doctors and pharmacies
    doctors_path = kiss_dir / "gesundheit-und-soziales" / "aerzte-und-apotheken.json"
    if doctors_path.exists():
        with open(doctors_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_doctors_pharmacies = data.get("rows", [])

    # Health & Social - rescue services
    rescue_path = kiss_dir / "gesundheit-und-soziales" / "rettungsdienst-einsaetze.json"
    if rescue_path.exists():
        with open(rescue_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_rescue_services = data.get("rows", [])

    # Construction & Housing - building completions
    construction_path = kiss_dir / "bautaetigkeit-und-wohnen" / "baufertigstellungen-nach-gebaeudeart.json"
    if construction_path.exists():
        with open(construction_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_construction_completions = data.get("rows", [])

    # Education & Culture - schools (Phase 2)
    schools_path = kiss_dir / "bildung-und-kultur" / "schulen-in-der-stadt-magdeburg.json"
    if schools_path.exists():
        with open(schools_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_schools = data.get("rows", [])

    # Tourism & Recreation - arrivals (Phase 2)
    tourism_arrivals_path = kiss_dir / "erholung-sport-und-fremdenverkehr" / "ankuenfte-der-gaeste-in-magdeburg.json"
    if tourism_arrivals_path.exists():
        with open(tourism_arrivals_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_tourism_arrivals = data.get("rows", [])

    # Tourism & Recreation - overnight stays (Phase 2)
    tourism_nights_path = kiss_dir / "erholung-sport-und-fremdenverkehr" / "anzahl-der-uebernachtungen-der-gaeste-in-magdeburg.json"
    if tourism_nights_path.exists():
        with open(tourism_nights_path, encoding="utf-8") as f:
            data = json.load(f)
        kiss_tourism_nights = data.get("rows", [])


def _load_stabstelle_klima():
    """Load Stabstelle Klima (Climate Office) datasets."""
    global climate_energy_emissions, climate_led_streetlights, climate_solar_energy

    climate_dir = DATA_DIR / "Stabstelle Klima"

    # Energy consumption and CO2 emissions
    energy_path = climate_dir / "energy_emissions.json"
    if energy_path.exists():
        with open(energy_path, encoding="utf-8") as f:
            climate_energy_emissions = json.load(f)

    # LED street lighting conversion
    led_path = climate_dir / "led_streetlights.json"
    if led_path.exists():
        with open(led_path, encoding="utf-8") as f:
            climate_led_streetlights = json.load(f)

    # Solar energy generation
    solar_path = climate_dir / "solar_energy.json"
    if solar_path.exists():
        with open(solar_path, encoding="utf-8") as f:
            climate_solar_energy = json.load(f)
