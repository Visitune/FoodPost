from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from classify import select_top_items
from sources import fetch_all, RawItem
from render_slides import render_article_to_pdf
from notify_email import send_notification
from themes import get_theme, get_all_themes

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def _demo_items() -> list[RawItem]:
    """Jeu de données fictif pour tester le rendu sans dépendre du réseau."""
    now = dt.datetime.now(dt.timezone.utc)
    return [
        RawItem(
            title="Rappel de fromages au lait cru pour suspicion de Listeria monocytogenes",
            summary=(
                "Un producteur régional a lancé un rappel volontaire sur plusieurs lots "
                "de fromages au lait cru après la détection de Listeria monocytogenes lors "
                "d'un autocontrôle. Aucun cas clinique confirmé à ce jour, distribution "
                "concernée : grande distribution et crémeries dans trois régions."
            ),
            source="RappelConso",
            url="https://rappel.conso.gouv.fr/fiche-rappel/exemple",
            published=now - dt.timedelta(hours=6),
            country="France",
        ),
        RawItem(
            title="Alerte RASFF : présence non déclarée d'allergène (moutarde) dans une sauce industrielle",
            summary=(
                "Le système RASFF signale la présence de moutarde non mentionnée sur "
                "l'étiquette d'une sauce condimentaire distribuée dans plusieurs pays "
                "européens. Le fabricant a été notifié et un retrait est en cours."
            ),
            source="RASFF",
            url="https://webgate.ec.europa.eu/rasff-window/",
            published=now - dt.timedelta(hours=20),
            country="Union Européenne",
        ),
    ]


def run(demo: bool, style: str, author_name: str, max_items: int, theme_id: str | None = None):
    OUTPUT_DIR.mkdir(exist_ok=True)

    if theme_id:
        from themes import get_theme_by_id
        theme = get_theme_by_id(theme_id)
    else:
        theme = get_theme()

    print(f"[main] Thème du jour : {theme['name']}")
    print(f"[main]   > {theme['editorial_angle']}")

    raw_items = _demo_items() if demo else fetch_all()
    print(f"[main] {len(raw_items)} articles bruts récupérés")

    top_items = select_top_items(raw_items, max_items=max_items)
    print(f"[main] {len(top_items)} article(s) retenu(s) comme très impactant(s)")
    for it in top_items:
        print(f"   - [{it.risk_level}] {it.title[:80]} (score={it.score})")

    if not top_items:
        print("[main] Rien d'assez impactant sur la période : pas de post généré aujourd'hui.")
        return

    pdf_paths = []
    summary_lines = []
    for i, item in enumerate(top_items, start=1):
        pdf_path = render_article_to_pdf(item, author_name, style, OUTPUT_DIR, index=i, theme=theme)
        pdf_paths.append(pdf_path)
        summary_lines.append(f"{item.title[:90]} -> {pdf_path.name}")
        print(f"[main] PDF généré : {pdf_path}")

    send_notification(pdf_paths, summary_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Utilise des données fictives (pas d'appel réseau)")
    parser.add_argument("--style", choices=["photo", "graphic"], default="graphic")
    parser.add_argument("--author", default="Votre nom")
    parser.add_argument("--max-items", type=int, default=2)
    parser.add_argument("--theme", default=None, help="ID du thème (défaut: auto basé sur la date)")
    parser.add_argument("--list-themes", action="store_true", help="Affiche la liste des thèmes disponibles")
    args = parser.parse_args()

    if args.list_themes:
        for t in get_all_themes():
            print(f"  {t['id']:20s} > {t['name']}")
        raise SystemExit(0)

    run(demo=args.demo, style=args.style, author_name=args.author, max_items=args.max_items, theme_id=args.theme)
