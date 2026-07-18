"""Icônes SVG simples et originales par catégorie (pas de librairie tierce -> pas de soucis de licence)."""

_WRAP = '<svg class="icon" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">{}</svg>'

ICONS = {
    "biologique": _WRAP.format(
        '<circle cx="32" cy="32" r="22"/><circle cx="24" cy="26" r="4"/>'
        '<circle cx="40" cy="24" r="3"/><circle cx="36" cy="40" r="3.5"/>'
    ),
    "allergene": _WRAP.format(
        '<path d="M32 8 L58 54 L6 54 Z" stroke-linejoin="round"/>'
        '<line x1="32" y1="24" x2="32" y2="38"/><circle cx="32" cy="46" r="1.6" stroke-width="3"/>'
    ),
    "corps_etranger": _WRAP.format(
        '<path d="M20 8 L40 20 L30 34 L44 30 L36 56 L18 40 L26 34 L14 30 Z" stroke-linejoin="round"/>'
    ),
    "chimique": _WRAP.format(
        '<path d="M26 8 h12 M28 8 v16 L14 50 a4 4 0 0 0 4 6 h28 a4 4 0 0 0 4-6 L36 24 V8" stroke-linejoin="round"/>'
        '<line x1="20" y1="40" x2="44" y2="40"/>'
    ),
    "reglementaire": _WRAP.format(
        '<line x1="32" y1="10" x2="32" y2="50"/>'
        '<line x1="14" y1="20" x2="50" y2="20"/>'
        '<path d="M14 20 L8 34 a10 8 0 0 0 12 0 Z"/>'
        '<path d="M50 20 L44 34 a10 8 0 0 0 12 0 Z"/>'
        '<line x1="22" y1="54" x2="42" y2="54"/>'
    ),
    "fraude": _WRAP.format(
        '<path d="M16 26 a16 16 0 0 1 32 0 v6 a16 16 0 0 1-32 0 Z"/>'
        '<circle cx="25" cy="27" r="2" stroke-width="4"/><circle cx="39" cy="27" r="2" stroke-width="4"/>'
        '<path d="M24 38 q8 6 16 0"/>'
    ),
    "autre": _WRAP.format(
        '<circle cx="32" cy="32" r="22"/><line x1="32" y1="20" x2="32" y2="34"/>'
        '<circle cx="32" cy="43" r="1.8" stroke-width="4"/>'
    ),
}

CATEGORY_LABELS = {
    "biologique": "Risque biologique",
    "allergene": "Allergène",
    "corps_etranger": "Corps étranger",
    "chimique": "Risque chimique",
    "reglementaire": "Réglementaire",
    "fraude": "Fraude alimentaire",
    "autre": "Sécurité des aliments",
}

RISK_LABELS = {
    "CRITICAL": ("CRITIQUE", "action immédiate"),
    "HIGH": ("ALERTE ÉLEVÉE", "vigilance requise"),
    "MEDIUM": ("SURVEILLANCE", "à suivre"),
    "LOW": ("INFO", "réglementaire"),
}

ACCENT = {
    "CRITICAL": "#D64545",
    "HIGH": "#E2A33D",
    "MEDIUM": "#2FA792",
    "LOW": "#7A8C93",
}
