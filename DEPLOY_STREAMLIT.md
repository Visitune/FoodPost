# Déployer sur Streamlit Community Cloud (gratuit, repo privé OK)

L'app tourne en **pur Python (Pillow)** : aucun navigateur, aucune dépendance
système. Elle se déploie donc directement sur Streamlit Community Cloud, y
compris depuis un **repo GitHub privé**, sans `packages.txt` ni bricolage.

## 1. Pousser le code sur GitHub

À la racine du projet :

```bash
git init
git add .
git commit -m "Veille food safety — app Streamlit (rendu Pillow)"
git branch -M main
# Crée d'abord un repo VIDE (privé) sur github.com, puis :
git remote add origin https://github.com/<ton-user>/<ton-repo>.git
git push -u origin main
```

> `.gitignore` exclut déjà `.env`, `output/`, `__pycache__/` et
> `.streamlit/secrets.toml`. Les secrets ne partent donc jamais sur GitHub.

## 2. Connecter Streamlit Community Cloud

1. Va sur **share.streamlit.io** et connecte-toi avec ton compte GitHub.
2. Autorise l'accès **y compris aux repos privés** (bouton « Grant access to
   private repositories » lors de l'autorisation GitHub). C'est ce qui permet
   de déployer un repo privé gratuitement.

## 3. Créer l'app

1. **New app** → sélectionne ton repo, la branche `main`, et **Main file
   path = `app.py`**.
2. **Deploy**. Streamlit installe `requirements.txt` (rapide, ~1 min) et lance
   l'app. Le **mode démo marche sans aucune clé**.

## 4. Renseigner les secrets (optionnel mais recommandé)

Dans l'app déployée : menu **⋮ → Settings → Secrets**, colle au format TOML :

```toml
GROQ_API_KEY = "gsk_..."   # rédaction de meilleure qualité (sinon fallback local) — gratuit sur console.groq.com
PEXELS_API_KEY = "..."     # uniquement pour le style "photo"
# GROQ_MODEL = "llama-3.3-70b-versatile"   # optionnel : change le modèle (défaut = openai/gpt-oss-120b)
```

`app.py` recopie automatiquement ces secrets dans les variables d'environnement,
donc le reste du code les utilise sans configuration supplémentaire.

> Pas besoin des secrets `EMAIL_*` ici : sur l'app tu **télécharges** le PDF
> directement, tu n'envoies pas d'email. Les `EMAIL_*` ne servent qu'au pipeline
> automatique GitHub Actions (`.github/workflows/veille.yml`).

## 5. Restreindre qui peut voir l'app (facultatif)

Par défaut l'URL est publique (non indexée). Dans **Settings → Sharing**, tu peux
limiter l'accès à une liste d'e-mails autorisés.

## Notes

- **Sources réseau réelles** (RappelConso / OpenFDA / RASFF) : elles peuvent être
  lentes ou limitées depuis l'infra cloud. Le **mode démo** fonctionne toujours ;
  pour le mode réel, laisse un `max-items` bas et sois patient au premier appel.
- **Ressources** : le tier gratuit dort après inactivité et se réveille en
  quelques secondes au prochain accès — normal.
