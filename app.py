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

from themes import get_all_themes, get_theme_by_id, category_for_theme
from classify import select_top_items
from sources import RawItem, fetch_all
from render_slides import render_article_to_pdf


def demo_items() -> list[RawItem]:
    """Jeu de démo couvrant plusieurs catégories (une par thème) pour que le
    choix d'un thème ramène bien un article cohérent et différent."""
    now = dt.datetime.now(dt.timezone.utc)
    return [
        RawItem(  # biologique -> thème Listeria
            title="Rappel de fromages au lait cru pour suspicion de Listeria monocytogenes",
            summary=(
                "Un producteur régional a lancé un rappel volontaire sur plusieurs lots "
                "de fromages au lait cru après la détection de Listeria monocytogenes lors "
                "d'un autocontrôle. Distribution en grande distribution dans trois régions."
            ),
            source="RappelConso",
            url="https://rappel.conso.gouv.fr/fiche-rappel/exemple",
            published=now - dt.timedelta(hours=6),
            country="France",
        ),
        RawItem(  # allergene -> thème Allergènes
            title="Alerte RASFF : présence non déclarée d'allergène (moutarde) dans une sauce",
            summary=(
                "Le système RASFF signale la présence d'un allergène (moutarde) non "
                "mentionné sur l'étiquette d'une sauce distribuée dans plusieurs pays "
                "européens. Le fabricant a été notifié et un retrait est en cours."
            ),
            source="RASFF",
            url="https://webgate.ec.europa.eu/rasff-window/",
            published=now - dt.timedelta(hours=20),
            country="Union Européenne",
        ),
        RawItem(  # chimique -> thème Chimique
            title="Dépassement des limites de résidus de pesticides dans des lots de thé importé",
            summary=(
                "Des résidus de pesticides supérieurs aux limites autorisées ont été "
                "détectés dans plusieurs lots de thé importé. Notification RASFF et retrait "
                "engagé dans plusieurs pays européens."
            ),
            source="RASFF",
            url="https://webgate.ec.europa.eu/rasff-window/",
            published=now - dt.timedelta(hours=30),
            country="Union Européenne",
        ),
        RawItem(  # corps_etranger -> thème Corps étrangers
            title="Rappel de plats préparés pour présence possible de morceaux de verre",
            summary=(
                "Un fabricant rappelle plusieurs lots de plats préparés distribués en "
                "grande distribution après la détection de corps étrangers (morceaux de "
                "verre). Aucun blessé signalé à ce jour."
            ),
            source="RappelConso",
            url="https://rappel.conso.gouv.fr/fiche-rappel/exemple2",
            published=now - dt.timedelta(hours=12),
            country="France",
        ),
        RawItem(  # fraude -> thème Fraude
            title="Suspicion de fraude sur l'authenticité d'huiles d'olive vierge extra",
            summary=(
                "Une enquête révèle une adultération et une tromperie sur l'authenticité "
                "de plusieurs huiles d'olive vierge extra vendues en Europe. Origine "
                "géographique non conforme à l'étiquetage annoncé."
            ),
            source="FoodSafetyNews",
            url="https://www.foodsafetynews.com/exemple-fraude",
            published=now - dt.timedelta(hours=40),
            country="Europe",
        ),
        RawItem(  # reglementaire -> thème Réglementaire
            title="Révision du règlement européen sur les contrôles officiels dans l'agroalimentaire",
            summary=(
                "La Commission européenne engage une révision du règlement sur les "
                "contrôles officiels. Un rapport et un avis EFSA accompagnent cette "
                "évolution attendue dans plusieurs pays européens."
            ),
            source="EFSA",
            url="https://www.efsa.europa.eu/exemple-reglement",
            published=now - dt.timedelta(hours=44),
            country="Union Européenne",
        ),
    ]


def generate(theme, style: str, author: str, max_items: int, use_demo: bool) -> list[dict]:
    raw_items = demo_items() if use_demo else fetch_all()
    # Thème imposé -> on filtre les articles sur sa catégorie (Auto = None = tout).
    category = category_for_theme(theme)
    top_items = select_top_items(raw_items, max_items=max_items, category=category)

    results = []
    for i, item in enumerate(top_items, start=1):
        pdf_path = render_article_to_pdf(item, author, style, OUTPUT_DIR, index=i, theme=theme)
        slide_pngs = [str(p) for j in range(1, 4)
                      if (p := OUTPUT_DIR / f"article{i}_slide{j}.png").exists()]
        post_path = OUTPUT_DIR / f"article{i}_post.txt"
        caption = post_path.read_text(encoding="utf-8") if post_path.exists() else ""
        results.append({
            "title": item.title,
            "source": item.source,
            "risk_level": item.risk_level,
            "pdf": str(pdf_path),
            "slides": slide_pngs,
            "caption": caption,
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

    AUTO_LABEL = "Auto (selon l'article)"
    selected_theme_name = st.selectbox("Thème visuel", [AUTO_LABEL] + theme_names, index=0)
    if selected_theme_name == AUTO_LABEL:
        selected_theme = None  # chaque article prendra le thème de sa catégorie
    else:
        selected_theme = get_theme_by_id(theme_ids[theme_names.index(selected_theme_name)])

    style = st.radio("Style de fond", ["graphic", "photo"], horizontal=True)
    author = st.text_input("Ton nom", value="VisiPilot")
    max_items = st.slider("Articles par run", 1, 3, 2)
    use_demo = st.checkbox("Mode démo (données fictives)", value=True)

    # Diagnostic Groq : dit clairement si la traduction/rédaction française marche.
    if not os.environ.get("GROQ_API_KEY"):
        st.warning(
            "Pas de clé **GROQ_API_KEY** → rédaction basique : le texte reste "
            "dans la langue de la source (ex. anglais). Ajoute la clé dans "
            "**Settings → Secrets** pour une rédaction **en français**."
        )
    else:
        if "groq_ok" not in st.session_state:
            from copywriter import check_groq
            st.session_state["groq_ok"], st.session_state["groq_msg"] = check_groq()
        if st.session_state["groq_ok"]:
            st.success(f"✅ {st.session_state['groq_msg']} — rédaction en français.")
        else:
            st.error(
                f"❌ {st.session_state['groq_msg']}\n\n"
                "→ Le texte restera dans la langue de la source. Vérifie la clé "
                "**GROQ_API_KEY** (et éventuellement **GROQ_MODEL**) dans les Secrets."
            )
        if st.button("Re-tester Groq", use_container_width=True):
            st.session_state.pop("groq_ok", None)
            st.rerun()
    if style == "photo" and not os.environ.get("PEXELS_API_KEY"):
        st.info(
            "Style **photo** sans **PEXELS_API_KEY** → fond dégradé par défaut. "
            "Ajoute la clé Pexels (gratuite) dans les Secrets pour de vraies photos."
        )

    st.markdown("---")
    st.caption(
        "En mode **Auto**, chaque article prend le thème de sa catégorie "
        "(couleurs et angle cohérents avec le contenu). Choisis un thème précis "
        "pour forcer le même style sur tous les articles."
    )

# --- MAIN ---
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### Lancer la génération")

    if st.button("Générer les diapos", use_container_width=True, type="primary"):
        with st.spinner("Génération en cours…"):
            try:
                results = generate(
                    theme=selected_theme,
                    style=style, author=author,
                    max_items=max_items, use_demo=use_demo,
                )
                if results:
                    st.session_state["generated"] = results
                    st.session_state["theme_name"] = (
                        selected_theme["name"] if selected_theme else "Automatique (selon l'article)"
                    )
                    st.success(f"{len(results)} PDF généré(s) !")
                elif selected_theme is not None:
                    st.warning(
                        f"Aucun article de la catégorie « {selected_theme['name']} » "
                        "sur la période. Essaie le mode **Auto** ou un autre thème."
                    )
                else:
                    st.warning(
                        "Aucun événement assez impactant sur la période "
                        "(normal hors mode démo si rien de CRITICAL/HIGH/récurrent récent)."
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

            if item.get("caption"):
                st.markdown("**📝 Texte du post LinkedIn** — copie-le dans ta publication :")
                st.text_area(
                    "Légende LinkedIn",
                    value=item["caption"],
                    height=240,
                    label_visibility="collapsed",
                    key=f"cap_{item['pdf']}",
                )
                st.download_button(
                    "Télécharger le texte (.txt)",
                    data=item["caption"],
                    file_name=f"{Path(item['pdf']).stem}_post.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"dlpost_{item['pdf']}",
                )

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
