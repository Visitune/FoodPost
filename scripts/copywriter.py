"""
Rédaction du contenu des 3 diapos.

Deux modes :
- Avec GROQ_API_KEY : un LLM Groq reformule proprement (accroche + reformulation
  factuelle + 3 points d'audit), à partir du résumé brut de la source.
- Sans clé : fallback heuristique local.

Groq est compatible avec l'API OpenAI (endpoint /chat/completions) et propose un
mode JSON (`response_format`) qui garantit une sortie JSON valide. On appelle
l'API en REST via `requests` : aucune dépendance supplémentaire à installer.

Modèle par défaut : `llama-3.3-70b-versatile` — le plus FIABLE pour du JSON
structuré en français (les modèles gpt-oss sont des modèles de raisonnement qui
gèrent parfois mal le mode JSON, ce qui provoque un repli silencieux en anglais).
Alternatives possibles via GROQ_MODEL :
  - openai/gpt-oss-120b       (le plus capable, mais mode JSON parfois capricieux)
  - openai/gpt-oss-20b        (rapide)
  - llama-3.1-8b-instant      (le plus rapide / le moins cher)
"""
from __future__ import annotations

import json
import os
import re

import requests

from icons import CATEGORY_LABELS

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

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


def _extract_json(text: str) -> dict:
    """Extrait un objet JSON même si le modèle l'entoure de texte ou de ```."""
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except Exception:
        m = _JSON_RE.search(text)
        if m:
            return json.loads(m.group(0))
        raise


def _post_groq(payload: dict, api_key: str, timeout: int = 30) -> str:
    resp = requests.post(
        GROQ_URL,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _groq_copy(system: str, user_content: str, api_key: str, model: str) -> dict:
    base = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.6,
        "max_tokens": 800,
    }
    # Tentative 1 : mode JSON strict. Tentative 2 (repli) : sans response_format,
    # car certains modèles (gpt-oss...) ne le supportent pas et échouent sinon.
    try:
        return _extract_json(_post_groq({**base, "response_format": {"type": "json_object"}}, api_key))
    except Exception:
        return _extract_json(_post_groq(base, api_key))


def check_groq() -> tuple[bool, str]:
    """Diagnostic : vérifie que Groq répond avec la clé/le modèle configurés."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return False, "Aucune clé GROQ_API_KEY détectée."
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    try:
        _post_groq(
            {
                "model": model,
                "messages": [{"role": "user", "content": "Réponds uniquement par: OK"}],
                "max_tokens": 5,
                "temperature": 0,
            },
            api_key,
            timeout=20,
        )
        return True, f"Groq actif (modèle {model})."
    except Exception as e:
        return False, f"Groq injoignable ({model}) : {e}"


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
            f"Niveau de risque : {item.risk_level} | Date : {item.published}\n"
            "Rappel : réponds en JSON, entièrement en FRANÇAIS."
        )

        model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
        data = _groq_copy(system, user_content, api_key, model)
        assert "headline" in data and "facts" in data
        if isinstance(data.get("facts"), str):
            data["facts"] = [data["facts"]]
        return data
    except Exception as e:
        print(f"[copywriter] fallback heuristique (raison: {e})")
        return _heuristic_copy(item, editorial_angle)
