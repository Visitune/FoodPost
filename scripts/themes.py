"""
Système de thèmes tournants pour les diapos LinkedIn.
Chaque thème combine un style visuel (couleurs, gradients) et un angle éditorial.
Rotation : un nouveau thème tous les 2 jours (basé sur le jour de l'année // 2).
"""
from __future__ import annotations

import datetime as dt


THEMES = [
    {
        "id": "listeria",
        "name": "Listeria & Microbiologie",
        "primary": "#B91C1C",
        "secondary": "#7F1D1D",
        "accent": "#EF4444",
        "accent_dim": "rgba(239,68,68,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 20% 50%, rgba(185,28,28,0.4) 0%, transparent 50%),"
            "radial-gradient(ellipse at 80% 20%, rgba(239,68,68,0.2) 0%, transparent 40%),"
            "radial-gradient(ellipse at 60% 80%, rgba(127,29,29,0.3) 0%, transparent 45%),"
            "linear-gradient(135deg, #0F0A0A 0%, #1A0E0E 40%, #120808 100%)"
        ),
        "pexels_query": "microbiology laboratory bacteria culture",
        "editorial_angle": "Microbiologie alimentaire, contaminations croisées, Listeria monocytogenes",
        "headline_prefix": "",
        "category_hints": ["biologique"],
    },
    {
        "id": "allergenes",
        "name": "Allergènes & Étiquetage",
        "primary": "#D97706",
        "secondary": "#92400E",
        "accent": "#F59E0B",
        "accent_dim": "rgba(245,158,11,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 70% 30%, rgba(217,119,6,0.35) 0%, transparent 50%),"
            "radial-gradient(ellipse at 20% 70%, rgba(245,158,11,0.15) 0%, transparent 40%),"
            "radial-gradient(ellipse at 90% 80%, rgba(146,64,14,0.25) 0%, transparent 45%),"
            "linear-gradient(160deg, #110D05 0%, #1A1208 40%, #0F0C04 100%)"
        ),
        "pexels_query": "food ingredients allergens labeling close up",
        "editorial_angle": "14 allergènes réglementaires, étiquetage, déclarations, risques croisés",
        "headline_prefix": "",
        "category_hints": ["allergene"],
    },
    {
        "id": "fraude",
        "name": "Fraude Alimentaire",
        "primary": "#7C3AED",
        "secondary": "#5B21B6",
        "accent": "#A78BFA",
        "accent_dim": "rgba(167,139,250,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 30% 40%, rgba(124,58,237,0.35) 0%, transparent 50%),"
            "radial-gradient(ellipse at 80% 60%, rgba(167,139,250,0.15) 0%, transparent 40%),"
            "radial-gradient(ellipse at 50% 90%, rgba(91,33,186,0.25) 0%, transparent 45%),"
            "linear-gradient(145deg, #0C0618 0%, #120A24 40%, #0A0514 100%)"
        ),
        "pexels_query": "food fraud adulteration investigation",
        "editorial_angle": "Fraude alimentaire, adulteration, authenticité, traçabilité, VACCP",
        "headline_prefix": "",
        "category_hints": ["fraude"],
    },
    {
        "id": "chimique",
        "name": "Risques Chimiques",
        "primary": "#0369A1",
        "secondary": "#075985",
        "accent": "#38BDF8",
        "accent_dim": "rgba(56,189,248,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 60% 20%, rgba(3,105,161,0.35) 0%, transparent 50%),"
            "radial-gradient(ellipse at 10% 60%, rgba(56,189,248,0.15) 0%, transparent 40%),"
            "radial-gradient(ellipse at 80% 80%, rgba(7,89,133,0.25) 0%, transparent 45%),"
            "linear-gradient(155deg, #040E18 0%, #061420 40%, #030B12 100%)"
        ),
        "pexels_query": "chemistry laboratory food testing analysis",
        "editorial_angle": "Pesticides, mycotoxines, contaminants chimiques, métaux lourds",
        "headline_prefix": "",
        "category_hints": ["chimique"],
    },
    {
        "id": "reglementaire",
        "name": "Réglementation & Normes",
        "primary": "#0D9488",
        "secondary": "#115E59",
        "accent": "#2DD4BF",
        "accent_dim": "rgba(45,212,191,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 40% 30%, rgba(13,148,136,0.3) 0%, transparent 50%),"
            "radial-gradient(ellipse at 80% 70%, rgba(45,212,191,0.12) 0%, transparent 40%),"
            "radial-gradient(ellipse at 20% 80%, rgba(17,94,89,0.25) 0%, transparent 45%),"
            "linear-gradient(150deg, #041210 0%, #061A17 40%, #030E0C 100%)"
        ),
        "pexels_query": "food safety regulation inspection document",
        "editorial_angle": "Nouveaux règlements, décrets, normes IFS/BRC, évolutions réglementaires",
        "headline_prefix": "",
        "category_hints": ["reglementaire"],
    },
    {
        "id": "corps_etranger",
        "name": "Corps Étrangers & Safety",
        "primary": "#64748B",
        "secondary": "#475569",
        "accent": "#94A3B8",
        "accent_dim": "rgba(148,163,184,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 50% 40%, rgba(100,116,139,0.3) 0%, transparent 50%),"
            "radial-gradient(ellipse at 20% 20%, rgba(148,163,184,0.12) 0%, transparent 40%),"
            "radial-gradient(ellipse at 80% 80%, rgba(71,85,105,0.25) 0%, transparent 45%),"
            "linear-gradient(140deg, #0A0F14 0%, #101820 40%, #080C10 100%)"
        ),
        "pexels_query": "food factory production line safety inspection",
        "editorial_angle": "Corps étrangers, safety, HACCP, contrôles physiques, metaux",
        "headline_prefix": "",
        "category_hints": ["corps_etranger"],
    },
    {
        "id": "alerte_generale",
        "name": "Alerte Générale & Tendances",
        "primary": "#6D28D9",
        "secondary": "#4C1D95",
        "accent": "#8B5CF6",
        "accent_dim": "rgba(139,92,246,0.15)",
        "gradient_css": (
            "radial-gradient(ellipse at 70% 30%, rgba(109,40,217,0.3) 0%, transparent 50%),"
            "radial-gradient(ellipse at 20% 60%, rgba(139,92,246,0.15) 0%, transparent 40%),"
            "radial-gradient(ellipse at 90% 80%, rgba(76,29,149,0.25) 0%, transparent 45%),"
            "linear-gradient(135deg, #08050F 0%, #0E0818 40%, #06040C 100%)"
        ),
        "pexels_query": "food industry trends analysis modern",
        "editorial_angle": "Tendances sectorielles, analyses croisées, veille stratégique food safety",
        "headline_prefix": "",
        "category_hints": [],
    },
]


def get_theme(date: dt.date | None = None) -> dict:
    """Retourne le thème du jour (rotation tous les 2 jours)."""
    if date is None:
        date = dt.date.today()
    idx = (date.timetuple().tm_yday // 2) % len(THEMES)
    return THEMES[idx]


def get_theme_by_id(theme_id: str) -> dict:
    """Retourne un thème par son ID."""
    for t in THEMES:
        if t["id"] == theme_id:
            return t
    return THEMES[0]


def get_all_themes() -> list[dict]:
    """Retourne la liste de tous les thèmes disponibles."""
    return THEMES
