"""
Récupération des données brutes depuis les sources de VISIwatch.
Exécuté côté serveur (GitHub Actions), donc pas besoin des proxys CORS
utilisés par la version navigateur de VISIwatch.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass, field

import requests
import feedparser

from config import RAPPELCONSO_URL, OPENFDA_URL, RSS_SOURCES, LOOKBACK_HOURS

HEADERS = {"User-Agent": "veille-foodsafety-linkedin/1.0"}

_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(text: str) -> str:
    """Retire les balises HTML et décode les entités (&#xa0;, &amp;...).

    Beaucoup de flux RSS renvoient du HTML dans le résumé ; sans nettoyage on
    retrouve des `<p>` et `&#xa0;` bruts sur les diapos.
    """
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class RawItem:
    title: str
    summary: str
    source: str
    url: str
    published: dt.datetime
    country: str = ""
    raw: dict = field(default_factory=dict)


def _cutoff(hours: int = LOOKBACK_HOURS) -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)


def fetch_rappelconso(hours: int = LOOKBACK_HOURS) -> list[RawItem]:
    """RappelConso (DGCCRF/DGAL) - rappels de produits alimentaires en France.

    Dataset Opendatasoft v2.1 « rappelconso-v2-gtin-espaces ». Champs v2 :
    date_publication, motif_rappel, risques_encourus, sous_categorie_produit,
    marque_produit, libelle, lien_vers_la_fiche_rappel.
    """
    params = {
        "limit": 50,
        "order_by": "date_publication desc",
        "where": 'categorie_produit="alimentation"',  # aliments uniquement
    }
    try:
        r = requests.get(RAPPELCONSO_URL + "/records", params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[RappelConso] erreur fetch: {e}")
        return []

    cutoff = _cutoff(hours)
    items = []
    for rec in data.get("results", []):
        pub_raw = rec.get("date_publication")
        if not pub_raw:
            continue
        try:
            pub = dt.datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if pub < cutoff:
            continue

        marque = clean_html(rec.get("marque_produit") or "")
        sous_cat = clean_html(rec.get("sous_categorie_produit") or "")
        libelle = clean_html(rec.get("libelle") or "")
        motif = clean_html(rec.get("motif_rappel") or "")
        risques = clean_html(rec.get("risques_encourus") or "")

        produit = libelle or sous_cat or "produit alimentaire"
        title = f"Rappel {produit}" + (f" — {marque}" if marque else "")
        # Le résumé porte le danger (motif + risques) : essentiel pour la classification.
        summary = " ".join(p for p in [motif, risques] if p).strip() or title

        items.append(
            RawItem(
                title=title,
                summary=summary,
                source="RappelConso",
                url=rec.get("lien_vers_la_fiche_rappel") or "https://rappel.conso.gouv.fr",
                published=pub,
                country="France",
                raw=rec,
            )
        )
    return items


def fetch_openfda(hours: int = LOOKBACK_HOURS) -> list[RawItem]:
    """OpenFDA - rappels alimentaires US (utile pour la veille internationale)."""
    cutoff = _cutoff(hours)
    date_from = cutoff.strftime("%Y%m%d")
    date_to = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    params = {
        "search": f"report_date:[{date_from}+TO+{date_to}]",
        "limit": 50,
        "sort": "report_date:desc",
    }
    try:
        r = requests.get(OPENFDA_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[OpenFDA] erreur fetch: {e}")
        return []

    items = []
    for rec in data.get("results", []):
        pub_raw = rec.get("report_date")
        if not pub_raw:
            continue
        try:
            pub = dt.datetime.strptime(pub_raw, "%Y%m%d").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        items.append(
            RawItem(
                title=clean_html(f"{rec.get('product_description', 'Produit')[:120]} — {rec.get('recalling_firm', '')}"),
                summary=clean_html(rec.get("reason_for_recall", "")),
                source="OpenFDA",
                url=f"https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
                published=pub,
                country="USA",
                raw=rec,
            )
        )
    return items


def fetch_rss(name: str, url: str, hours: int = LOOKBACK_HOURS) -> list[RawItem]:
    """Flux RSS génériques (RASFF, presse spécialisée, LégiFrance agro...)."""
    cutoff = _cutoff(hours)
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
    except Exception as e:
        print(f"[{name}] erreur fetch RSS: {e}")
        return []

    items = []
    for entry in feed.entries:
        pub = None
        for field_name in ("published_parsed", "updated_parsed"):
            if getattr(entry, field_name, None):
                pub = dt.datetime(*getattr(entry, field_name)[:6], tzinfo=dt.timezone.utc)
                break
        if pub is None or pub < cutoff:
            continue
        items.append(
            RawItem(
                title=clean_html(entry.get("title", "")),
                summary=clean_html(entry.get("summary", "")),
                source=name,
                url=entry.get("link", url),
                published=pub,
            )
        )
    return items


def fetch_all(hours: int = LOOKBACK_HOURS) -> list[RawItem]:
    all_items: list[RawItem] = []
    all_items += fetch_rappelconso(hours)
    all_items += fetch_openfda(hours)
    for name, url in RSS_SOURCES.items():
        all_items += fetch_rss(name, url, hours)
    return all_items
