# Veille Food Safety → LinkedIn (basé sur VISIwatch)

Pipeline qui tourne tous les 2 jours, reprend la logique de sources et de
classification de [VISIwatch](https://github.com/Visitune/VISIwatch) côté
serveur (donc sans les proxys CORS de la version navigateur), sélectionne le
ou les 1-2 événements les plus impactants, et génère un carrousel PDF
(**3 diapos, format paysage 1920×1080**) prêt à poster, avec **thème visuel
tournant** et branding **VisiPilot**.

**Ce que fait le pipeline automatiquement :**
1. Récupère RappelConso, OpenFDA, RASFF, presse spécialisée, LégiFrance
2. Filtre sur la pertinence agroalimentaire + classe le risque (CRITICAL / HIGH / MEDIUM / LOW)
3. Score et sélectionne les 1-2 événements les plus impactants des dernières 48h
4. Sélectionne le thème visuel du jour (rotation tous les 2 jours, 7 thèmes)
5. Rédige l'accroche + le résumé + 3 points d'audit (via Claude si une clé API est fournie, sinon un mode local sobre)
6. Génère un PDF 3 diapos par événement (rendu Pillow : mesh gradients, panneaux translucides, tampon de risque, logo VisiPilot)
7. T'envoie un email avec les PDF en pièce jointe pour relecture

**Ce qu'il ne fait volontairement pas :** poster automatiquement sur LinkedIn.
L'API LinkedIn pour les posts "document" nécessite une validation d'app
(Marketing Developer Platform) assez lourde pour un usage perso ; le rapport
coût/bénéfice n'en valait pas la peine vs. juste glisser le PDF reçu par mail
dans un post LinkedIn (30 secondes, et tu gardes le contrôle éditorial avant
publication — ce que tu avais demandé).

## Installation

```bash
git clone <ton fork de VISIwatch, ou nouveau repo>
cd veille-linkedin
pip install -r requirements.txt
```

Le rendu est en **pur Python (Pillow)** : aucun navigateur headless à installer.

## Interface web (Streamlit)

```bash
streamlit run app.py
```

Puis règle les paramètres et clique sur **Générer les diapos**. Pour la mettre en
ligne gratuitement (repo privé possible), voir **[DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md)**.

## Test immédiat en ligne de commande (sans réseau, données fictives)

```bash
cd scripts
python main.py --demo --style graphic --author "Ton Nom"
```

Les PDF sortent dans `output/`.

## Système de thèmes tournants

Un nouveau thème visuel est sélectionné automatiquement tous les 2 jours.
Chaque thème combine un style visuel (couleurs, mesh gradients) et un angle
éditorial qui oriente la rédaction du contenu.

| Thème | Couleurs | Angle éditorial |
|---|---|---|
| `listeria` | Rouge foncé → noir | Microbiologie, contaminations croisées |
| `allergenes` | Orange → ambre | 14 allergènes, étiquetage, déclarations |
| `fraude` | Violet → magenta | Authenticité, traçabilité, VACCP |
| `chimique` | Bleu foncé → cyan | Pesticides, mycotoxines, contaminants |
| `reglementaire` | Teal → vert | Nouveaux règlements, normes IFS/BRC |
| `corps_etranger` | Gris acier → blanc | Safety, HACCP, contrôles physiques |
| `alerte_generale` | Dark navy → violet | Tendances, analyses sectorielles |

```bash
# Lister le thème du jour
python main.py --list-themes

# Forcer un thème spécifique
python main.py --demo --theme listeria
```

## Secrets GitHub Actions à configurer

Dans `Settings > Secrets and variables > Actions` du repo :

| Secret | Obligatoire | Rôle |
|---|---|---|
| `EMAIL_USER` | oui (pour recevoir le mail) | adresse d'envoi (ex: Gmail) |
| `EMAIL_PASS` | oui | mot de passe d'application (**pas** ton mot de passe normal — [créer un app password Gmail](https://myaccount.google.com/apppasswords)) |
| `EMAIL_TO` | non (défaut = EMAIL_USER) | destinataire si différent |
| `EMAIL_HOST` / `EMAIL_PORT` | non (défaut Gmail) | si tu utilises un autre fournisseur |
| `GROQ_API_KEY` | recommandé | pour une rédaction de meilleure qualité (sinon fallback basique) — gratuit sur [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | non | modèle Groq (défaut `openai/gpt-oss-120b`) |
| `PEXELS_API_KEY` | non | pour le style "photo" (gratuit sur [pexels.com/api](https://www.pexels.com/api/)) |

Variable (pas secret) optionnelle : `AUTHOR_NAME` (ton nom affiché en pied de diapo).

Le workflow est déjà dans `.github/workflows/veille.yml`, cron toutes les 48h.
Tu peux aussi le lancer manuellement depuis l'onglet Actions ("Run workflow")
avec choix du thème et du style.

## Poster sur LinkedIn

1. Tu reçois l'email avec le/les PDF
2. Nouveau post LinkedIn → icône document → glisser le PDF → LinkedIn l'affiche automatiquement en carrousel swipable
3. Rédige 2-3 lignes d'intro (ton avis d'auditeur ajoute la valeur que le PDF ne peut pas remplacer)

## Personnalisation

- **Sources** : `scripts/config.py` → `RSS_SOURCES`. L'URL RASFF indiquée est
  celle du portail RASFF Window actuel ; comme ces flux changent parfois de
  format, vérifie-la une fois avant le premier run réel (`curl` l'URL et
  regarde si tu obtiens bien du XML). Idem pour l'agrégateur LégiFrance.
- **Mots-clés de risque / catégories** : `scripts/config.py`
- **Thèmes** : `scripts/themes.py` → liste `THEMES`. Tu peux ajouter/modifier
  des thèmes (couleurs, gradient CSS, angle éditorial, requête Pexels).
- **Design** : `templates/slide.html` — mesh gradients CSS, glassmorphism,
  logo VisiPilot en watermark + footer, `.stamp` = tampon d'audit signature.
- **Nombre d'articles/run** : `--max-items` (défaut 2, respecte donc bien "1 ou 2" demandé)
- **Logo** : remplacer `logo 04 copie.jpg` à la racine du projet par ton propre logo.

## Structure

```
scripts/
  config.py        sources + mots-clés + scoring
  themes.py         7 thèmes visuels + éditoriaux tournants
  sources.py        fetchers RappelConso / OpenFDA / RSS
  classify.py       filtre agro + classification risque + sélection top N
  copywriter.py     rédaction (Claude ou fallback local) avec angle éditorial
  icons.py          libellés + couleurs par catégorie/risque
  render_slides.py  rendu pur Pillow -> PNG -> PDF (thème, logo, tampon intégrés)
  notify_email.py   email avec PDF en pièce jointe (pipeline GitHub Actions)
  main.py           orchestration + CLI (--theme, --style, --list-themes)
app.py              interface web Streamlit (déployable sur Streamlit Cloud)
assets/fonts/       polices TTF bundlées (rendu identique partout)
logo 04 copie.jpg   logo VisiPilot (watermark + footer)
templates/slide.html   ancien template HTML (legacy, plus utilisé pour le rendu)
.github/workflows/veille.yml   cron GitHub Actions toutes les 48h
```
