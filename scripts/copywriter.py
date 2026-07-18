"""
Rédaction du contenu des 3 diapos.

Deux modes :
- Avec GROQ_API_KEY : un LLM Groq reformule proprement (accroche + reformulation
  factuelle + 3 points d'audit), à partir du résumé brut de la source.
- Sans clé : fallback heuristique local.

Groq est compatible avec l'API OpenAI (endpoint /chat/completions) et propose un
mode JSON (`response_format`) qui garantit une sortie JSON valide. On appelle
l'API en REST via `requests` : aucune dépendance supplémentaire à installer.

Modèle par défaut : `openai/gpt-oss-120b` (le plus capable de la gamme Groq,
rapide et bon marché). Alternatives possibles via GROQ_MODEL :
  - llama-3.3-70b-versatile   (très bon suivi d'instructions FR)
  - openai/gpt-oss-20b        (plus rapide, un peu moins fin)
  - llama-3.1-8b-instant      (le plus rapide / le moins cher)
"""
from __future__ import annotations

import json
import os

import requests

from icons import CATEGORY_LABELS

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """Tu rédiges le contenu d'un carrousel LinkedIn de 3 diapos pour un \
consultant/auditeur food safety qui fait de la veille réglementaire et sanitaire \
en Europe. Ton lectorat : responsables qualité, RSE, auditeurs IFS/BRC, industriels \
agroalimentaires. Ton sérieux, factuel, jamais sensationnaliste. Tu reformules \
TOUJOURS avec tes propres mots (jamais de copier-coller du texte source).

RÈGLE ABSOLUE : tu écris TOUJOURS en FRANÇAIS, même si la source est en anglais \
ou dans une autre langue — tu traduis et reformules en français impeccable. \
Aucun mot d'anglais, aucune balise HTML dans ta réponse.

{editorial_context}

Réponds UNIQUEMENT en JSON valide, sans texte autour, avec ce schéma exact :
{{
  "headline": "accroche courte percutante, 6-10 mots, sans point final",
  "body_text": "reformulation factuelle en 2-3 phrases (35-45 mots), ce qui s'est passé",
  "facts": ["point d'audit concret 1 (max 14 mots)", "point 2", "point 3"],
  "cta_headline": "phrase de synthèse courte (5-8 mots)",
  "cta_title": "titre d'accroche pour l'appel à l'action (max 6 mots)",
  "cta_sub": "1 phrase engageante invitant à suivre la veille, max 20 mots"
}}"""


def _truncate(text: str, limit: int) -> str:
    """Coupe proprement à la frontière de mot, sans laisser un mot à moitié."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return f"{cut}…"


def _heuristic_copy(item, editorial_angle: str = "") -> dict:
    cat_label = CATEGORY_LABELS.get(item.category, "Sécurité des aliments")
    body = _truncate(item.summary, 240) or f"Alerte {cat_label.lower()} rapportée par {item.source} le {item.published}."
    return {
        "headline": _truncate(item.title, 68),
        "body_text": body,
        "facts": [
            f"Source : {item.source}, publié le {item.published}",
            f"Catégorie de risque : {cat_label}",
            "Vérifiez vos fournisseurs et références concernées par ce type de produit",
        ],
        "cta_headline": "Une veille food safety à jour, tous les 2 jours",
        "cta_title": "Restez informé",
        "cta_sub": "Je partage ici les alertes food safety les plus impactantes pour vos audits.",
    }


def generate_copy(item, editorial_angle: str = "") -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return _heuristic_copy(item, editorial_angle)

    try:
        editorial_context = ""
        if editorial_angle:
            editorial_context = (
                f"ANGLE ÉDITORIAL DU JOUR : {editorial_angle}. "
                "Adapte le ton et les points d'audit en fonction de cet angle."
            )

        system = SYSTEM_PROMPT.format(editorial_context=editorial_context)
        user_content = (
            f"Titre source : {item.title}\n"
            f"Résumé source : {item.summary[:600]}\n"
            f"Source : {item.source} | Pays/zone : {item.country} | "
            f"Catégorie : {CATEGORY_LABELS.get(item.category, item.category)} | "
            f"Niveau de risque : {item.risk_level} | Date : {item.published}"
        )

        payload = {
            "model": os.environ.get("GROQ_MODEL", DEFAULT_MODEL),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(
            GROQ_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        # En mode JSON la sortie est déjà propre ; on nettoie quand même par sécurité.
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        assert "headline" in data and "facts" in data
        return data
    except Exception as e:
        print(f"[copywriter] fallback heuristique (raison: {e})")
        return _heuristic_copy(item, editorial_angle)
