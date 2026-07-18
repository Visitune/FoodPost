"""
Filtrage, classification et scoring : détermine quels articles sont
"très impactants" et méritent une diapo.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import (
    KEYWORDS_AGRO, RISK_KEYWORDS, RISK_WEIGHT, SEVERITY_BOOST_WORDS,
    CATEGORY_RULES, MAX_ITEMS_PER_RUN,
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


def select_top_items(raw_items: list[RawItem], max_items: int = MAX_ITEMS_PER_RUN) -> list[ScoredItem]:
    scored = []
    for item in raw_items:
        if not is_agro_relevant(item):
            continue
        risk = classify_risk(item)
        cat = classify_category(item)
        s = score_item(item, risk)
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
                score=s,
            )
        )
    scored = _dedupe(scored)
    scored.sort(key=lambda x: x.score, reverse=True)

    # On ne garde que du CRITICAL/HIGH pour respecter la consigne
    # "très impactant" ; fallback sur MEDIUM si rien de mieux ce jour-là.
    strong = [s for s in scored if s.risk_level in ("CRITICAL", "HIGH")]
    pool = strong if strong else scored
    return pool[:max_items]
