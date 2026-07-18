"""
Moteur de rendu 100 % Pillow (aucun navigateur, aucune dépendance binaire).

Remplace l'ancien rendu HTML -> Playwright/Chromium -> PDF, qui ne pouvait pas
tourner de façon fiable sur Streamlit Community Cloud (~1 Go RAM, pas de Chromium).

On dessine directement les 3 diapos (1920x1080) avec Pillow : dégradé « mesh »
approximé, panneaux translucides, logo VisiPilot, tampon de risque, texte mis en
page avec des polices TTF bundlées (assets/fonts). Puis on assemble en PDF.

La signature publique `render_article_to_pdf(...)` est inchangée pour que
`main.py`, l'app Streamlit et le workflow GitHub Actions continuent de marcher.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from icons import CATEGORY_LABELS, RISK_LABELS
from themes import get_theme_for_category

ROOT = Path(__file__).parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"
LOGO_PATH = ROOT / "logo 04 copie.jpg"

SLIDE_W, SLIDE_H = 1920, 1080

# Palette de base (identique à l'ancien template)
PAPER = (233, 236, 234)       # #E9ECEA
PAPER_DIM = (175, 192, 190)   # #AFC0BE

# Contenu FIXE de la diapo finale (CTA) — met en avant les prestations VisiPilot.
# Fixe (et non généré par l'IA) pour un branding cohérent d'un post à l'autre.
VISIPILOT_CTA = {
    "kicker": "VISIPILOT · VEILLE · IA · DIGITALISATION",
    "headline": "La veille sécurité des aliments, augmentée par l'IA",
    "services": [
        "Veille réglementaire & sanitaire en continu",
        "Outils IA pour la qualité et vos audits",
        "Digitalisation de vos process (IFS, BRCGS, HACCP)",
    ],
    "cta": "Découvrez nos solutions",
    "url": "www.visipilot.com",
}

PEXELS_QUERY_BY_CATEGORY = {
    "biologique": "microbiology laboratory food",
    "allergene": "food ingredients close up",
    "corps_etranger": "food factory production line",
    "chimique": "chemistry laboratory analysis",
    "reglementaire": "food inspection warehouse",
    "fraude": "food packaging industry",
    "autre": "food industry factory",
}

_FONT_FILES = {
    "display": "ArchivoBlack-Regular.ttf",
    "sans": "Inter-Regular.ttf",
    "mono": "JetBrainsMono-Regular.ttf",
}


# --------------------------------------------------------------------------- #
# Helpers couleurs
# --------------------------------------------------------------------------- #
def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _darken_hex(hex_color: str, amount: int = 60) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r, g, b = max(0, r - amount), max(0, g - amount), max(0, b - amount)
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------- #
# Polices
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=64)
def _font(family: str, size: int, weight: str | None = None) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / _FONT_FILES[family]
    try:
        f = ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()
    if weight and family != "display":
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


# --------------------------------------------------------------------------- #
# Logo (fond blanc -> transparent pour garder uniquement la marque colorée)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _logo_rgba() -> Image.Image | None:
    if not LOGO_PATH.exists():
        return None
    logo = Image.open(LOGO_PATH).convert("RGBA")
    px = logo.getdata()
    out = []
    for r, g, b, a in px:
        if r > 232 and g > 232 and b > 232:
            out.append((r, g, b, 0))
        else:
            out.append((r, g, b, a))
    logo.putdata(out)
    return logo


def _paste_logo(base: Image.Image, box_w: int, xy: tuple[int, int], opacity: float = 1.0):
    logo = _logo_rgba()
    if logo is None:
        return
    ratio = box_w / logo.width
    lg = logo.resize((box_w, max(1, int(logo.height * ratio))), Image.LANCZOS)
    if opacity < 1.0:
        alpha = lg.split()[3].point(lambda a: int(a * opacity))
        lg.putalpha(alpha)
    base.paste(lg, xy, lg)


# --------------------------------------------------------------------------- #
# Fond « mesh gradient »
# --------------------------------------------------------------------------- #
def _paste_glow(bg: Image.Image, cx: int, cy: int, diameter: int, color: tuple[int, int, int], strength: float):
    """Colle une tache radiale douce (approxime les mesh gradients CSS)."""
    rad = ImageOps.invert(Image.radial_gradient("L")).resize((diameter, diameter))
    rad = rad.point(lambda a: int(a * strength))
    glow = Image.new("RGB", (diameter, diameter), color)
    bg.paste(glow, (cx - diameter // 2, cy - diameter // 2), rad)


def _apply_left_shade(bg: Image.Image) -> Image.Image:
    """Assombrit le tiers gauche (dégradé horizontal) pour garantir le contraste
    du texte blanc, tout en laissant la couleur vive s'exprimer à droite."""
    shade = Image.new("L", (SLIDE_W, 1))
    for x in range(SLIDE_W):
        t = x / (SLIDE_W - 1)
        shade.putpixel((x, 0), int(max(0.0, 175 * (1 - t / 0.55))))
    shade = shade.resize((SLIDE_W, SLIDE_H))
    black = Image.new("RGB", (SLIDE_W, SLIDE_H), (0, 0, 0))
    return Image.composite(black, bg, shade)


def _make_background(theme: dict, photo_url: str | None = None) -> Image.Image:
    # Moins de noircissement -> couleurs de thème plus riches et vivantes.
    top = _hex_to_rgb(_darken_hex(theme["primary"], 32))
    bot = _hex_to_rgb(_darken_hex(theme["secondary"], 74))

    bg = Image.new("RGB", (SLIDE_W, SLIDE_H), bot)
    d = ImageDraw.Draw(bg)
    for y in range(SLIDE_H):
        t = y / (SLIDE_H - 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        d.line([(0, y), (SLIDE_W, y)], fill=(r, g, b))

    primary = _hex_to_rgb(theme["primary"])
    accent = _hex_to_rgb(theme["accent"])
    secondary = _hex_to_rgb(theme["secondary"])
    _paste_glow(bg, int(SLIDE_W * 0.32), int(SLIDE_H * 0.28), 1500, primary, 0.75)
    _paste_glow(bg, int(SLIDE_W * 0.88), int(SLIDE_H * 0.12), 1150, accent, 0.55)
    _paste_glow(bg, int(SLIDE_W * 0.72), int(SLIDE_H * 0.92), 1350, secondary, 0.60)
    _paste_glow(bg, int(SLIDE_W * 0.60), int(SLIDE_H * 0.55), 950, accent, 0.30)
    bg = bg.filter(ImageFilter.GaussianBlur(72))

    if photo_url:
        try:
            resp = requests.get(photo_url, timeout=15)
            resp.raise_for_status()
            from io import BytesIO
            photo = Image.open(BytesIO(resp.content)).convert("RGB")
            photo = ImageOps.fit(photo, (SLIDE_W, SLIDE_H), Image.LANCZOS)
            # 1) assombrir la photo pour la lisibilité du texte blanc
            photo = Image.blend(photo, Image.new("RGB", (SLIDE_W, SLIDE_H), (0, 0, 0)), 0.45)
            # 2) teinter avec le dégradé du thème -> la photo épouse la couleur du thème
            bg = Image.blend(photo, bg, 0.5)
        except Exception as e:
            print(f"[render] photo ignorée, fallback dégradé (raison: {e})")

    # Voile sombre à gauche pour le contraste du texte (après la photo).
    bg = _apply_left_shade(bg)
    # On garde le fond en RGB : le blending alpha de Pillow (Draw(im, "RGBA"))
    # ne s'active que lorsqu'on dessine SUR une image RGB.
    return bg


# --------------------------------------------------------------------------- #
# Pexels (style photo)
# --------------------------------------------------------------------------- #
def fetch_pexels_photo(query: str) -> str | None:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None
    query = query or "food safety industry"
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            headers={"Authorization": api_key},
            timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        return photos[0]["src"]["landscape"]
    except Exception as e:
        print(f"[Pexels] fallback gradient (raison: {e})")
        return None


# --------------------------------------------------------------------------- #
# Helpers texte
# --------------------------------------------------------------------------- #
def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if not cur or draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_lines(draw, lines, xy, font, fill, line_h):
    x, y = xy
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=fill)
        y += line_h
    return y


def _draw_eyebrow(draw, base, accent, date_str, theme_name):
    x, y = 64, 60
    draw.ellipse([x, y + 6, x + 12, y + 18], fill=accent)
    mono = _font("mono", 20, "Medium")
    label = f"VEILLE SÉCURITÉ DES ALIMENTS  ·  {date_str}"
    draw.text((x + 26, y), label, font=mono, fill=PAPER_DIM)
    lx = x + 26 + draw.textlength(label, font=mono) + 28
    # tag thème
    tag_font = _font("mono", 17, "Medium")
    tw = draw.textlength(theme_name.upper(), font=tag_font)
    draw.rounded_rectangle([lx, y - 4, lx + tw + 36, y + 26], radius=16,
                           fill=accent + (28,), outline=accent + (120,), width=1)
    draw.text((lx + 18, y + 1), theme_name.upper(), font=tag_font, fill=accent)


def _draw_footer(base, draw, author_name, page_idx, page_total):
    y = SLIDE_H - 78
    _paste_logo(base, 120, (64, y - 4))
    brand_font = _font("mono", 20, "Medium")
    draw.text((196, y + 6), f"{author_name}", font=_font("mono", 21, "Bold"), fill=PAPER)
    draw.text((196 + draw.textlength(author_name, font=_font('mono', 21, 'Bold')) + 10, y + 8),
              "— Consultant & auditeur sécurité des aliments", font=brand_font, fill=PAPER_DIM)
    page_txt = f"{page_idx} / {page_total}"
    draw.text((SLIDE_W - 64 - draw.textlength(page_txt, font=brand_font), y + 8),
              page_txt, font=brand_font, fill=PAPER_DIM)


def _draw_stamp(base, accent, risk_label, risk_sub):
    S = 320
    m = 30
    inner_w = S - 2 * m - 26
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([m, m, S - m, S - m], outline=accent, width=6, fill=(0, 0, 0, 90))
    d.ellipse([m + 18, m + 18, S - m - 18, S - m - 18], outline=accent + (140,), width=2)

    # Auto-ajuste la taille de police pour que le libellé tienne dans le badge,
    # puis répartit sur 1-2 lignes (ex. "ALERTE ÉLEVÉE", "SURVEILLANCE").
    size = 42
    while size > 22:
        f = _font("mono", size, "Bold")
        if max(d.textlength(w, font=f) for w in risk_label.split()) <= inner_w:
            break
        size -= 2
    f_main = _font("mono", size, "Bold")
    lines = _wrap(d, risk_label, f_main, inner_w) or [risk_label]
    line_h = size + 6
    f_sub = _font("mono", 22, "Medium")

    total_h = len(lines) * line_h + 34
    y = (S - total_h) / 2
    for ln in lines:
        w = d.textlength(ln, font=f_main)
        d.text(((S - w) / 2, y), ln, font=f_main, fill=accent)
        y += line_h
    sw = d.textlength(risk_sub, font=f_sub)
    d.text(((S - sw) / 2, y + 6), risk_sub, font=f_sub, fill=accent + (220,))

    layer = layer.rotate(-9, expand=True, resample=Image.BICUBIC)
    base.paste(layer, (SLIDE_W - 52 - layer.width, 40), layer)


def _panel(draw, box, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=(255, 255, 255, 12),
                           outline=(255, 255, 255, 40), width=1)


def _section_title(draw, text, xy, accent):
    draw.text(xy, text.upper(), font=_font("mono", 20, "Bold"), fill=accent)


# --------------------------------------------------------------------------- #
# Slides
# --------------------------------------------------------------------------- #
def _base_slide(theme, accent, date_str, photo_url, page_idx, author_name,
                risk_label, risk_sub):
    base = _make_background(theme, photo_url)
    _paste_logo(base, 620, ((SLIDE_W - 620) // 2, (SLIDE_H - 620) // 2), opacity=0.06)
    draw = ImageDraw.Draw(base, "RGBA")
    # Bande d'accent verticale à gauche (signature éditoriale)
    draw.rectangle([0, 0, 7, SLIDE_H], fill=accent + (255,))
    _draw_eyebrow(draw, base, accent, date_str, theme["name"])
    _draw_stamp(base, accent, risk_label, risk_sub)
    _draw_footer(base, draw, author_name, page_idx, 3)
    return base, draw


def _slide_hook(ctx):
    base, draw = _base_slide(**ctx["base"])
    accent = ctx["accent"]
    # chip catégorie
    chip_font = _font("mono", 22, "Bold")
    cat = ctx["category_label"].upper()
    cw = draw.textlength(cat, font=chip_font)
    draw.rounded_rectangle([64, 250, 64 + cw + 44, 300], radius=14,
                           fill=accent + (30,), outline=accent + (150,), width=1)
    draw.text((64 + 22, 258), cat, font=chip_font, fill=accent)

    # headline
    hl_font = _font("display", 78)
    lines = _wrap(draw, ctx["headline"], hl_font, 1080)
    y = _draw_lines(draw, lines, (64, 340), hl_font, PAPER, 92)

    # soulignement d'accent sous le titre
    draw.line([(66, y + 22), (286, y + 22)], fill=accent + (255,), width=6)

    # kicker
    k_font = _font("mono", 22, "Medium")
    kb_font = _font("mono", 22, "Bold")
    ky = y + 58
    kx = 64
    for label, val in [("SOURCE", ctx["source"]), ("ZONE", ctx["country"]),
                       ("CATÉGORIE", ctx["category_label"])]:
        draw.text((kx, ky), label + " ", font=k_font, fill=PAPER_DIM)
        kx += draw.textlength(label + "  ", font=k_font)
        draw.text((kx, ky), val, font=kb_font, fill=PAPER)
        kx += draw.textlength(val, font=kb_font) + 48

    # panneau angle éditorial (colonne droite)
    px0 = SLIDE_W - 64 - 460
    _panel(draw, [px0, 360, SLIDE_W - 64, 640])
    _section_title(draw, "Angle éditorial", (px0 + 32, 392), accent)
    ang_font = _font("sans", 26, "Regular")
    ang_lines = _wrap(draw, ctx["editorial_angle"], ang_font, 396)
    _draw_lines(draw, ang_lines, (px0 + 32, 436), ang_font, PAPER_DIM, 38)
    return base


def _slide_detail(ctx):
    base, draw = _base_slide(**ctx["base"])
    accent = ctx["accent"]
    left_w = 1050

    _section_title(draw, "Ce qu'il s'est passé", (64, 232), accent)
    body_font = _font("sans", 30, "Medium")
    body_lines = _wrap(draw, ctx["body_text"], body_font, left_w)
    y = _draw_lines(draw, body_lines, (64, 278), body_font, PAPER, 44)

    y += 20
    draw.line([(64, y), (64 + left_w, y)], fill=accent + (180,), width=2)
    y += 34

    _section_title(draw, "Points clés à retenir", (64, y), accent)
    y += 48
    fact_font = _font("sans", 26, "Regular")
    marker_font = _font("mono", 22, "Bold")
    for i, fact in enumerate(ctx["facts"], start=1):
        draw.text((64, y + 2), f"{i:02d}", font=marker_font, fill=accent)
        f_lines = _wrap(draw, fact, fact_font, left_w - 66)
        y = _draw_lines(draw, f_lines, (64 + 62, y), fact_font, PAPER, 36) + 14

    # Source à consulter : source · date · lien (bas de la colonne gauche)
    y = max(y + 20, 848)
    _section_title(draw, "Source à consulter", (64, y), accent)
    draw.text((64, y + 30), f"{ctx['source']}  ·  {ctx['date']}",
              font=_font("mono", 21, "Bold"), fill=PAPER)
    url_font = _font("mono", 19, "Regular")
    url_lines = _wrap(draw, str(ctx["url"]), url_font, left_w)
    _draw_lines(draw, url_lines, (64, y + 62), url_font, PAPER_DIM, 26)

    # panneau récap (droite) — placé sous le tampon pour éviter le chevauchement
    px0 = SLIDE_W - 64 - 460
    _panel(draw, [px0, 412, SLIDE_W - 64, 812], radius=20)
    _section_title(draw, "Résumé rapide", (px0 + 32, 446), accent)
    ry = 502
    sm = _font("sans", 24, "Regular")
    smb = _font("sans", 24, "SemiBold")
    for label, val, col in [("Source", ctx["source"], PAPER),
                            ("Zone", ctx["country"], PAPER),
                            ("Catégorie", ctx["category_label"], PAPER),
                            ("Niveau", ctx["risk_label"], accent)]:
        draw.text((px0 + 32, ry), f"{label} :", font=smb, fill=PAPER)
        lx = px0 + 32 + draw.textlength(f"{label} :  ", font=smb)
        vlines = _wrap(draw, str(val), sm, (SLIDE_W - 64) - lx - 20)
        ry = _draw_lines(draw, vlines, (lx, ry), sm, col, 34) + 16
    return base


def _slide_cta(ctx):
    """Diapo finale : appel à l'action VisiPilot (veille, IA, digitalisation)."""
    base, draw = _base_slide(**ctx["base"])
    accent = ctx["accent"]
    cx = SLIDE_W // 2

    # kicker
    kf = _font("mono", 22, "Bold")
    kick = VISIPILOT_CTA["kicker"]
    kw = draw.textlength(kick, font=kf)
    draw.text((cx - kw / 2, 296), kick, font=kf, fill=accent)

    # headline (centrée, sous le tampon)
    hl_font = _font("display", 60)
    lines = _wrap(draw, VISIPILOT_CTA["headline"], hl_font, 1180)
    y = 352
    for ln in lines:
        w = draw.textlength(ln, font=hl_font)
        draw.text((cx - w / 2, y), ln, font=hl_font, fill=PAPER)
        y += 74
    # soulignement d'accent centré
    draw.line([(cx - 90, y + 18), (cx + 90, y + 18)], fill=accent + (255,), width=6)

    # panneau des prestations
    y += 62
    pw = 1160
    px0 = cx - pw // 2
    rows = VISIPILOT_CTA["services"]
    row_h = 62
    ph = 40 + len(rows) * row_h
    _panel(draw, [px0, y, px0 + pw, y + ph], radius=18)
    sf = _font("sans", 30, "Medium")
    ry = y + 28
    for r in rows:
        draw.ellipse([px0 + 40, ry + 13, px0 + 56, ry + 29], fill=accent + (255,))
        draw.text((px0 + 82, ry), r, font=sf, fill=PAPER)
        ry += row_h
    y += ph + 36

    # bouton CTA rempli (style "pro")
    cf = _font("mono", 27, "Bold")
    cta = VISIPILOT_CTA["cta"] + "   →"
    cw = draw.textlength(cta, font=cf)
    bw = cw + 92
    bx0 = cx - bw // 2
    draw.rounded_rectangle([bx0, y, bx0 + bw, y + 72], radius=14, fill=accent + (255,))
    draw.text((cx - cw / 2, y + 21), cta, font=cf, fill=(12, 16, 22))

    # URL du site, bien visible
    uf = _font("mono", 30, "Bold")
    url = VISIPILOT_CTA["url"]
    uw = draw.textlength(url, font=uf)
    draw.text((cx - uw / 2, y + 96), url, font=uf, fill=accent)
    return base


# --------------------------------------------------------------------------- #
# Point d'entrée public (signature inchangée)
# --------------------------------------------------------------------------- #
def render_article_to_pdf(item, author_name: str, style: str, out_dir: Path,
                          index: int, theme: dict | None = None) -> Path:
    """style: 'photo' ou 'graphic'. theme: dict du thème visuel. Retourne le chemin du PDF."""
    from copywriter import generate_copy

    # Par défaut, le thème découle de la CATÉGORIE de l'article (cohérence
    # visuelle + éditoriale). Un thème explicite (choix manuel) reste prioritaire.
    if theme is None:
        theme = get_theme_for_category(item.category)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    copy = generate_copy(item)
    # L'accent suit le THÈME (cohérence chromatique) et non le risque : le niveau
    # de risque reste communiqué par le tampon et le champ « Niveau ».
    accent = _hex_to_rgb(theme["accent"])
    risk_label, risk_sub = RISK_LABELS.get(item.risk_level, RISK_LABELS["MEDIUM"])
    category_label = CATEGORY_LABELS.get(item.category, "Sécurité des aliments")

    photo_url = None
    if style == "photo":
        # Photo adaptée au THÈME (requête dédiée dans themes.py), avec repli catégorie.
        photo_query = theme.get("pexels_query") or PEXELS_QUERY_BY_CATEGORY.get(item.category, "food industry")
        photo_url = fetch_pexels_photo(photo_query)

    def base_ctx(page_idx):
        return dict(
            theme=theme, accent=accent, date_str=item.published, photo_url=photo_url,
            page_idx=page_idx, author_name=author_name,
            risk_label=risk_label, risk_sub=risk_sub,
        )

    common = dict(
        accent=accent, source=item.source, country=item.country,
        category_label=category_label, editorial_angle=theme.get("editorial_angle", ""),
        risk_label=risk_label, url=item.url, date=item.published,
    )

    slides = [
        _slide_hook({**common, "base": base_ctx(1), "headline": copy["headline"]}),
        _slide_detail({**common, "base": base_ctx(2),
                       "body_text": copy["body_text"], "facts": copy["facts"]}),
        _slide_cta({**common, "base": base_ctx(3)}),
    ]

    png_paths = []
    for i, img in enumerate(slides, start=1):
        rgb = img.convert("RGB")
        png_path = out_dir / f"article{index}_slide{i}.png"
        rgb.save(png_path)
        png_paths.append(rgb)

    pdf_path = out_dir / f"veille_{item.risk_level.lower()}_{index}.pdf"
    png_paths[0].save(pdf_path, save_all=True, append_images=png_paths[1:])
    return pdf_path
