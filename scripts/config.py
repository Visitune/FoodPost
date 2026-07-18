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
    "rappelconso-v2-gtin-espaces"
)

OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"

# Flux RSS. A ajuster librement : ce sont de simples URLs, pas de code à toucher.
RSS_SOURCES = {
    "RASFF": "https://webgate.ec.europa.eu/rasff-window/screen/rss",  # souvent vide (RSS déprécié)
    "FoodSafetyNews": "https://www.foodsafetynews.com/feed/",
    "EFSA": "https://www.efsa.europa.eu/en/news/rss",
    "Food Safety Magazine": "https://www.food-safety.com/rss/articles",
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
    # termes anglais (EFSA, Food Safety Magazine)
    "safety", "allergen", "pesticide", "outbreak", "hazard", "efsa", "hygiene",
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
# INTÉRÊT ÉDITORIAL — au-delà de la gravité brute
# ---------------------------------------------------------------------------
# Un simple rappel produit isolé, s'il n'est ni alarmant ni récurrent, n'a pas
# d'intérêt pour une audience d'auditeurs/qualiticiens. Ces signaux repèrent ce
# qui vaut vraiment la peine d'être commenté : ampleur, dimension épidémique,
# enjeu réglementaire/systémique, fraude, étude/rapport.
INTEREST_KEYWORDS = [
    # ampleur / diffusion
    "plusieurs pays", "multi-pays", "national", "europe", "union européenne",
    "rappel massif", "plusieurs lots", "grande distribution",
    # dimension épidémique / sanitaire lourde
    "hospitalis", "décès", "deces", "mort", "épidémie", "epidemie",
    "cluster", "cas groupés", "cas groupes", "toxi-infection", "tiac", "foyer",
    # dimension systémique / réglementaire / enquête
    "étude", "etude", "efsa", "anses", "enquête", "enquete", "rapport",
    "tendance", "nouveau règlement", "nouveau reglement", "règlement", "reglement",
    "directive", "décret", "decret", "norme", "audit",
    # fraude / authenticité
    "fraude", "adultération", "adulteration", "authenticité", "authenticite",
    "non déclaré", "non declare", "non déclarée", "non declaree", "tromperie",
    # récurrence explicite
    "récurrent", "recurrent", "systémique", "systemique", "en hausse",
    # signaux anglais (EFSA, Food Safety Magazine, FoodSafetyNews)
    "outbreak", "recall", "recalled", "warning", "illness", "hospitaliz",
    "death", "nationwide", "multistate", "ban", "regulation", "guidance",
    "study", "report", "assessment", "contamination", "undeclared",
]
INTEREST_WEIGHT = 8          # points par signal d'intérêt trouvé

# Récurrence : une même catégorie qui revient sur la période = tendance à commenter.
RECURRENCE_WEIGHT = 14       # points par occurrence supplémentaire de la catégorie

# Seuil d'intérêt minimal pour retenir un item "non alarmant" (MEDIUM/LOW).
# En dessous, on considère que c'est un rappel banal et on ne le retient pas.
MIN_INTEREST_SCORE = 12

# ---------------------------------------------------------------------------
# CATEGORISATION VISUELLE (pour choisir l'iconographie / le thème des diapos)
# ---------------------------------------------------------------------------

# Mots-clés FR + EN (les sources EFSA / Food Safety Magazine sont en anglais).
CATEGORY_RULES = {
    "biologique": ["listeria", "salmonella", "e.coli", "e. coli", "bactérie", "bacterie",
                   "botulis", "listeriosis", "salmonellosis", "norovirus", "campylobacter",
                   "pathogen", "bacteria", "outbreak"],
    "allergene": ["allergène", "allergene", "gluten", "lait", "arachide", "fruits à coque",
                  "allergen", "undeclared", "milk", "peanut", "soy", "egg", "sesame", "tree nut"],
    "corps_etranger": ["verre", "glass", "métal", "metal", "plastique", "plastic",
                       "corps étranger", "foreign body", "foreign material"],
    "chimique": ["pesticide", "mycotoxine", "mercure", "cyanure", "toxine", "toxin",
                 "mycotoxin", "heavy metal", "chemical", "residue", "contaminant",
                 "lead", "dioxin", "aflatoxin", "histamine"],
    "reglementaire": ["décret", "decret", "loi", "jorf", "arrêté", "arrete", "règlement",
                      "regulation", "directive", "guidance", "legislation", "compliance", "law"],
    "fraude": ["fraude", "tromperie", "étiquetage", "etiquetage", "fraud", "adulteration",
               "authenticity", "counterfeit", "mislabel", "food crime"],
}

# Nombre d'articles retenus par run (1 ou 2, selon la consigne)
MAX_ITEMS_PER_RUN = 2
LOOKBACK_HOURS = 48
