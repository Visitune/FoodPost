# Lancer le pipeline depuis VS Code

Guide pas-à-pas, du dézippage au premier PDF généré.

## 1. Ouvrir le projet

1. Dézippe `veille-foodsafety-linkedin.zip` quelque part sur ton disque
2. VS Code → `Fichier > Ouvrir le dossier...` → sélectionne le dossier dézippé
3. Ouvre un terminal intégré : `Terminal > Nouveau terminal` (ou `` Ctrl+` ``)

## 2. Créer l'environnement Python

Dans le terminal VS Code, à la racine du projet :

```bash
python3 -m venv .venv
```

Puis active-le :

- **macOS / Linux** : `source .venv/bin/activate`
- **Windows (PowerShell)** : `.venv\Scripts\Activate.ps1`
- **Windows (cmd)** : `.venv\Scripts\activate.bat`

Ton terminal doit maintenant afficher `(.venv)` au début de la ligne.
Vérifie aussi en bas à droite de VS Code que l'interpréteur Python sélectionné
pointe bien vers `.venv` (sinon clique dessus → choisis `./.venv/bin/python`).

## 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

C'est tout : le rendu est en **pur Python (Pillow)**, il n'y a **aucun navigateur
à installer** (plus de Playwright/Chromium). Les polices sont bundlées dans
`assets/fonts/`.

## 4. Premier test (sans réseau, données fictives)

```bash
cd scripts
python main.py --demo --style graphic --author "Ton Nom"
```

Tu dois voir dans le terminal :

```
[main] 2 articles bruts récupérés
[main] 1 ou 2 article(s) retenu(s) comme très impactant(s)
[main] PDF généré : .../output/veille_critical_1.pdf
[email] EMAIL_USER / EMAIL_PASS non configurés : notification ignorée.
```

Ouvre le(s) PDF généré(s) dans `output/` (clic droit → Révéler dans
l'explorateur, ou glisse-le dans VS Code) pour vérifier le rendu.

Si tu as une erreur `ModuleNotFoundError`, l'environnement virtuel n'est
probablement pas activé — refais l'étape 2.

## 5. Configurer tes clés (mode réel)

Crée un fichier `.env` à la racine du projet (à côté de `requirements.txt`) :

```env
GROQ_API_KEY=gsk_...
PEXELS_API_KEY=...
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=toi@gmail.com
EMAIL_PASS=xxxx xxxx xxxx xxxx
EMAIL_TO=toi@gmail.com
```

- `GROQ_API_KEY` : optionnel mais recommandé, pour une rédaction de meilleure
  qualité (sinon fallback local basique). **Gratuit** sur
  [console.groq.com](https://console.groq.com). Modèle par défaut
  `openai/gpt-oss-120b` ; tu peux le changer avec `GROQ_MODEL=...`.
- `PEXELS_API_KEY` : optionnel, uniquement si tu veux le style `photo`.
  Gratuit sur [pexels.com/api](https://www.pexels.com/api/).
- `EMAIL_PASS` : pour Gmail, ce n'est **pas** ton mot de passe habituel mais
  un "mot de passe d'application" à créer sur
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
  (nécessite la validation en 2 étapes activée sur le compte Google).

Le `.env` est chargé automatiquement par `main.py`. **Ne le commite jamais**
sur GitHub — ajoute cette ligne à un fichier `.gitignore` à la racine :

```bash
echo ".env" >> .gitignore
echo ".venv" >> .gitignore
```

## 6. Lancer en conditions réelles

```bash
python main.py --style graphic --author "Ton Nom" --max-items 2
```

Ça va interroger RappelConso / OpenFDA / RASFF / presse pour de vrai. Si
aucun événement CRITICAL/HIGH n'est trouvé sur les dernières 48h, le script
te le dit et ne génère rien (comportement normal, pas un bug).

## 7. Automatiser (GitHub Actions)

Une fois que le rendu local te convient :

1. Crée un repo GitHub (ou utilise ton fork de VISIwatch) et pousse ce dossier
   (le `.github/workflows/veille.yml` est déjà prêt)
2. `Settings > Secrets and variables > Actions > New repository secret` :
   ajoute `GROQ_API_KEY`, `PEXELS_API_KEY`, `EMAIL_HOST`, `EMAIL_PORT`,
   `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_TO` (mêmes valeurs que ton `.env`)
3. Onglet `Actions` → le workflow `Veille food safety LinkedIn` apparaît,
   tu peux le lancer manuellement (`Run workflow`) pour vérifier avant
   d'attendre le prochain cron (toutes les 48h automatiquement)

## Débogage rapide

| Symptôme | Cause probable |
|---|---|
| `ModuleNotFoundError` | `.venv` pas activé, ou dépendances pas installées |
| Texte mal rendu / police par défaut | dossier `assets/fonts/` absent ou incomplet (les 3 `.ttf` doivent être présents) |
| `[email] EMAIL_USER / EMAIL_PASS non configurés` | `.env` absent ou mal placé (doit être à la racine, pas dans `scripts/`) |
| `[copywriter] fallback heuristique` dans les logs | `GROQ_API_KEY` absente ou invalide — pas bloquant, juste moins bien rédigé |
| Rien n'est généré, `[main] Rien d'assez impactant` | normal si pas de CRITICAL/HIGH récent — pas une erreur |
