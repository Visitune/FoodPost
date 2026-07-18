"""
Veille Food Safety LinkedIn — Interface Web (Streamlit)
Génère les carrousels PDF directement dans le navigateur.

Rendu 100 % Pillow (aucun navigateur headless) → fonctionne tel quel sur
Streamlit Community Cloud, y compris depuis un repo GitHub privé.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import traceback
from pathlib import Path

import streamlit as st

SCRIPTS_DIR = Path(__file__).parent / "scripts"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS_DIR))

# --- Bridge secrets Streamlit -> variables d'environnement ---
# copywriter.py / render_slides.py lisent os.environ (GROQ_API_KEY,
# PEXELS_API_KEY...). Sur Streamlit Cloud, les secrets vivent dans st.secrets ;
# on les recopie dans l'environnement pour que le reste du code marche sans modif.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

from themes import get_all_themes, get_theme, get_theme_by_id
from classify import select_top_items
from sources import RawItem, fetch_all
from render_slides import render_article_to_pdf


def demo_items() -> list[RawItem]:
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
            title="Alerte RASFF : présence non déclarée d'allergène (moutarde) dans une sauce",
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


def generate(theme: dict, style: str, author: str, max_items: int, use_demo: bool) -> list[dict]:
    raw_items = demo_items() if use_demo else fetch_all()
    top_items = select_top_items(raw_items, max_items=max_items)

    results = []
    for i, item in enumerate(top_items, start=1):
        pdf_path = render_article_to_pdf(item, author, style, OUTPUT_DIR, index=i, theme=theme)
        slide_pngs = [str(p) for j in range(1, 4)
                      if (p := OUTPUT_DIR / f"article{i}_slide{j}.png").exists()]
        results.append({
            "title": item.title,
            "source": item.source,
            "risk_level": item.risk_level,
            "pdf": str(pdf_path),
            "slides": slide_pngs,
        })
    return results


# --- CONFIG STREAMLIT ---
st.set_page_config(
    page_title="Veille Food Safety — VisiPilot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS CUSTOM ---
st.markdown("""
<style>
    .stApp { background-color: #0B1120; }
    .block-container { max-width: 1100px; padding-top: 2rem; }
    h1, h2, h3 { color: #E9ECEA !important; }
    .stSelectbox label, .stTextInput label, .stRadio label, .stSlider label {
        color: #AFC0BE !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #F97316, #EA580C) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.75rem 2rem !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(249,115,22,0.4) !important;
    }
    .theme-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
    .theme-card h4 { color: #E9ECEA; margin: 0 0 4px 0; font-size: 0.95rem; }
    .theme-card p { color: #AFC0BE; margin: 0; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("# Veille Food Safety")
st.markdown("**Générateur de diapos LinkedIn** — VisiPilot.com")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## Paramètres")

    theme_list = get_all_themes()
    theme_names = [t["name"] for t in theme_list]
    theme_ids = [t["id"] for t in theme_list]

    selected_theme_name = st.selectbox("Thème visuel", theme_names, index=0)
    selected_theme_id = theme_ids[theme_names.index(selected_theme_name)]

    style = st.radio("Style de fond", ["graphic", "photo"], horizontal=True)
    author = st.text_input("Ton nom", value="VisiPilot")
    max_items = st.slider("Articles par run", 1, 3, 2)
    use_demo = st.checkbox("Mode démo (données fictives)", value=True)

    # État des clés (explique pourquoi le texte peut rester en anglais / sans photo)
    if not os.environ.get("GROQ_API_KEY"):
        st.warning(
            "Pas de clé **GROQ_API_KEY** → rédaction basique : le texte peut rester "
            "dans la langue de la source (ex. anglais). Ajoute la clé dans "
            "**Settings → Secrets** pour une rédaction propre **en français**."
        )
    if style == "photo" and not os.environ.get("PEXELS_API_KEY"):
        st.info(
            "Style **photo** sans **PEXELS_API_KEY** → fond dégradé par défaut. "
            "Ajoute la clé Pexels (gratuite) dans les Secrets pour de vraies photos."
        )

    st.markdown("---")
    st.markdown("#### Thème du jour")
    today_theme = get_theme()
    st.markdown(f"**{today_theme['name']}**")
    st.caption(today_theme['editorial_angle'])

# --- MAIN ---
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### Lancer la génération")

    if st.button("Générer les diapos", use_container_width=True, type="primary"):
        with st.spinner("Génération en cours…"):
            try:
                results = generate(
                    theme=get_theme_by_id(selected_theme_id),
                    style=style, author=author,
                    max_items=max_items, use_demo=use_demo,
                )
                if results:
                    st.session_state["generated"] = results
                    st.session_state["theme_name"] = get_theme_by_id(selected_theme_id)["name"]
                    st.success(f"{len(results)} PDF généré(s) !")
                else:
                    st.warning(
                        "Aucun événement assez impactant sur la période "
                        "(normal hors mode démo si rien de CRITICAL/HIGH récent)."
                    )
            except Exception as e:
                st.error(f"Erreur lors de la génération : {e}")
                st.code(traceback.format_exc())

with col2:
    st.markdown("### Résultats")

    if "generated" in st.session_state:
        st.markdown(f"Thème : **{st.session_state['theme_name']}**")

        for item in st.session_state["generated"]:
            st.markdown(f"#### {item['title'][:60]}…")
            st.caption(f"Source : {item['source']} | Risque : {item['risk_level']}")

            pdf_path = Path(item["pdf"])
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=f"Télécharger {pdf_path.name}",
                        data=f,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_{pdf_path.name}",
                    )

            slide_cols = st.columns(3)
            for j, png_str in enumerate(item.get("slides", [])):
                png_path = Path(png_str)
                if png_path.exists():
                    with slide_cols[j]:
                        st.image(str(png_path), caption=f"Slide {j+1}", use_container_width=True)

            st.markdown("---")
    else:
        st.markdown("Configure les paramètres à gauche puis clique sur **Générer les diapos**.")
        st.markdown("")
        st.markdown("#### Thèmes disponibles")
        for t in theme_list:
            st.markdown(f"""
            <div class="theme-card">
                <h4>{t['name']}</h4>
                <p>{t['editorial_angle']}</p>
            </div>
            """, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("---")
st.markdown(
    '<div style="text-align:center; color:#6B7280; font-size:0.8rem;">'
    'VisiPilot.com — Consultant &amp; auditeur food safety'
    '</div>',
    unsafe_allow_html=True,
)
