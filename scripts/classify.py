"""
Filtrage, classification et scoring : détermine quels articles sont
"très impactants" et méritent une diapo.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from config import (
    KEYWORDS_AGRO, RISK_KEYWORDS, RISK_WEIGHT, SEVERITY_BOOST_WORDS,
    CATEGORY_RULES, MAX_ITEMS_PER_RUN,
    INTEREST_KEYWORDS, INTEREST_WEIGHT, RECURRENCE_WEIGHT, MIN_INTEREST_SCORE,
)
from sources import RawItem


@dataclass
class ScoredItem:
    title: str
    summary: str
    source: str
    url: str
    published: str  # formaté pour affichage
    country: str
    risk_level: str
    category: str
    score: int
    interest: int = 0  # score d'intérêt éditorial (ampleur, récurrence, enjeu)


def _text(item: RawItem) -> str:
    return f"{item.title} {item.summary}".lower()


def is_agro_relevant(item: RawItem) -> bool:
    t = _text(item)
    # Ces sources sont déjà 100% alimentaires par construction
    if item.source in ("RappelConso", "OpenFDA", "RASFF"):
        return True
    return any(kw in t for kw in KEYWORDS_AGRO)


def classify_risk(item: RawItem) -> str:
    t = _text(item)
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if any(kw in t for kw in RISK_KEYWORDS[level]):
            return level
    return "LOW"


def classify_category(item: RawItem) -> str:
    t = _text(item)
    for cat, kws in CATEGORY_RULES.items():
        if any(kw in t for kw in kws):
            return cat
    return "autre"


def score_item(item: RawItem, risk_level: str) -> int:
    t = _text(item)
    score = RISK_WEIGHT[risk_level]
    score += 5 * sum(1 for w in SEVERITY_BOOST_WORDS if w in t)
    # Bonus fraîcheur : plus récent = plus haut
    import datetime as dt
    hours_old = (dt.datetime.now(dt.timezone.utc) - item.published).total_seconds() / 3600
    score += max(0, 10 - int(hours_old / 4.8))  # dégressif sur 48h
    return score


def interest_score(item: RawItem, category: str, category_counts: Counter) -> int:
    """Mesure l'intérêt éditorial d'un item, indépendamment de sa gravité brute :
    ampleur/diffusion, dimension épidémique, enjeu réglementaire/fraude, et
    récurrence de la catégorie sur la période (signal de tendance)."""
    t = _text(item)
    hits = sum(1 for w in INTEREST_KEYWORDS if w in t)
    score = INTEREST_WEIGHT * hits
    score += RECURRENCE_WEIGHT * max(0, category_counts.get(category, 0) - 1)
    return score


def _dedupe(items: list[ScoredItem]) -> list[ScoredItem]:
    seen = set()
    out = []
    for it in items:
        key = it.title.strip().lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def select_top_items(raw_items: list[RawItem], max_items: int = MAX_ITEMS_PER_RUN,
                     category: str | None = None) -> list[ScoredItem]:
    """Sélectionne les meilleurs articles. Si `category` est fourni (thème imposé),
    on ne garde que les articles de CETTE catégorie -> un thème choisi ramène bien
    un article correspondant, pas toujours le même top global."""
    # 1. Filtrage agro + pré-classification (nécessaire pour compter les récurrences)
    prelim = []
    for item in raw_items:
        if not is_agro_relevant(item):
            continue
        cat = classify_category(item)
        if category and cat != category:
            continue
        prelim.append((item, classify_risk(item), cat))

    # 2. Récurrence : combien de fois chaque catégorie apparaît sur la période
    category_counts = Counter(cat for _, _, cat in prelim)

    # 3. Scoring : gravité (score) + intérêt éditorial (interest)
    scored = []
    for item, risk, cat in prelim:
        inter = interest_score(item, cat, category_counts)
        base = score_item(item, risk)
        scored.append(
            ScoredItem(
                title=item.title.strip(),
                summary=(item.summary or "").strip(),
                source=item.source,
                url=item.url,
                published=item.published.strftime("%d/%m/%Y"),
                country=item.country or "Europe",
                risk_level=risk,
                category=cat,
                score=base + inter,
                interest=inter,
            )
        )

    scored = _dedupe(scored)
    scored.sort(key=lambda x: x.score, reverse=True)

    # 4. Sélection exigeante : on ne retient QUE ce qui est vraiment "postable" —
    #    soit ALARMANT (CRITICAL/HIGH), soit RÉCURRENT/à fort enjeu éditorial
    #    (interest >= seuil). Un rappel produit isolé et banal est écarté.
    def worth_posting(s: ScoredItem) -> bool:
        alarming = s.risk_level in ("CRITICAL", "HIGH")
        recurrent = category_counts.get(s.category, 0) >= 2
        return alarming or recurrent or s.interest >= MIN_INTEREST_SCORE

    pool = [s for s in scored if worth_posting(s)]  # trié par score décroissant

    # Thème imposé : déjà filtré sur la catégorie -> on prend les meilleurs.
    if category is not None:
        return pool[:max_items]

    # Mode Auto : diversifier les catégories pour éviter un carrousel monothématique
    # (ex. une semaine "tout Listeria" ne doit pas donner 3 fois le même sujet).
    buckets: dict[str, list[ScoredItem]] = defaultdict(list)
    for s in pool:
        buckets[s.category].append(s)
    cat_order = sorted(buckets, key=lambda c: buckets[c][0].score, reverse=True)
    result: list[ScoredItem] = []
    i = 0
    while len(result) < max_items and any(buckets.values()):
        cat = cat_order[i % len(cat_order)]
        if buckets[cat]:
            result.append(buckets[cat].pop(0))
        i += 1
    return result
