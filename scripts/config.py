"""
Configuration du pipeline de veille food safety.
Reprend la logique de filtrage/scoring de VISIwatch (services/externalDataService.ts)
mais côté serveur (Python), donc sans les soucis de CORS rencontrés côté navigateur.
"""

# ---------------------------------------------------------------------------
# SOURCES
# ---------------------------------------------------------------------------

RAPPELCONSO_URL = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "rappelconso-v2-gtin-espaces/records"
)

OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"

# Flux RSS. A ajuster librement : ce sont de simples URLs, pas de code à toucher.
RSS_SOURCES = {
    "RASFF": "https://webgate.ec.europa.eu/rasff-window/screen/rss",
    "FoodSafetyNews": "https://www.foodsafetynews.com/feed/",
    "LegiFrance (agro)": "https://legifrss.org/rss/jorf.xml",
}

# ---------------------------------------------------------------------------
# FILTRAGE METIER (garder uniquement ce qui concerne l'agroalimentaire)
# ---------------------------------------------------------------------------

KEYWORDS_AGRO = [
    "aliment", "agri", "pêche", "peche", "sanitaire", "hygiène", "hygiene",
    "santé", "sante", "consom", "fraude", "veterinaire", "vétérinaire",
    "eau", "environnement", "bio", "durable", "aoc", "aop", "label",
    "additif", "emballage", "bactérie", "bacterie", "lait", "viande",
    "vin", "food", "recall", "contamination", "listeria", "salmonella",
]

# ---------------------------------------------------------------------------
# CLASSIFICATION DU RISQUE (heuristique par mots-clés, comme VISIwatch)
# ---------------------------------------------------------------------------

RISK_KEYWORDS = {
    "CRITICAL": [
        "listeria", "salmonella", "e.coli", "e. coli", "botulis", "mort",
        "décès", "deces", "recall", "danger", "hospitalis", "clostridium",
        "mercure", "cyanure", "intoxication grave",
    ],
    "HIGH": [
        "allergène", "allergene", "toxin", "toxine", "glass", "verre",
        "metal", "métal", "corps étranger", "corps etranger", "pesticide",
        "mycotoxine", "salmonelle",
    ],
    "MEDIUM": [
        "hygiène", "hygiene", "qualité", "qualite", "inspection",
        "non-conformité", "non conformite", "étiquetage", "etiquetage",
    ],
    "LOW": [
        "décret", "decret", "loi", "jorf", "arrêté", "arrete",
    ],
}

RISK_WEIGHT = {"CRITICAL": 100, "HIGH": 60, "MEDIUM": 25, "LOW": 5}

# Petit bonus de "gravité" si ces mots apparaissent en plus (renforce le score
# sans changer la classification) — sert à départager plusieurs CRITICAL.
SEVERITY_BOOST_WORDS = [
    "décès", "deces", "mort", "hospitalis", "plusieurs pays",
    "rappel massif", "national", "europe", "union européenne",
]

# ---------------------------------------------------------------------------
# CATEGORISATION VISUELLE (pour choisir l'iconographie / le thème des diapos)
# ---------------------------------------------------------------------------

CATEGORY_RULES = {
    "biologique": ["listeria", "salmonella", "e.coli", "e. coli", "bactérie", "bacterie", "botulis"],
    "allergene": ["allergène", "allergene", "gluten", "lait", "arachide", "fruits à coque"],
    "corps_etranger": ["verre", "glass", "métal", "metal", "plastique", "corps étranger"],
    "chimique": ["pesticide", "mycotoxine", "mercure", "cyanure", "toxine", "toxin"],
    "reglementaire": ["décret", "decret", "loi", "jorf", "arrêté", "arrete", "règlement"],
    "fraude": ["fraude", "tromperie", "étiquetage", "etiquetage"],
}

# Nombre d'articles retenus par run (1 ou 2, selon la consigne)
MAX_ITEMS_PER_RUN = 2
LOOKBACK_HOURS = 48
