# Comment pousser ce projet sur GitHub

Étapes à exécuter dans **ton** terminal local. Je ne peux pas le faire à ta
place car je n'ai pas accès à ton compte GitHub depuis cet environnement.

## 1. Créer le dépôt sur GitHub (depuis ton navigateur)

1. Va sur https://github.com/new
2. **Repository name** : par exemple `reassurance-xl-mtpl-pricing` ou
   `actuarial-portfolio-reassurance`
3. **Visibility** : Public
4. **Surtout ne coche pas** : "Add a README", "Add .gitignore", "Add a license"
   → ils existent déjà dans le projet, on évite un conflit au premier push.
5. Clique sur **Create repository**.

GitHub t'affichera ensuite l'URL du dépôt, du genre :
```
https://github.com/<ton-username>/reassurance-xl-mtpl-pricing.git
```
Garde-la sous la main pour l'étape 3.

## 2. Initialiser Git dans ce dossier (la première fois seulement)

Ouvre **PowerShell** ou **CMD** dans le dossier du projet :
```
cd C:\Users\etudiant\Documents\Claude\Projects\reassurance
```

Configure Git (à faire une fois pour toutes sur ta machine, si tu ne l'as
pas déjà fait) :
```bash
git config --global user.name "Steve"
git config --global user.email "vanessandjiki0@gmail.com"
```

Puis initialise le dépôt local :
```bash
git init
git branch -M main
git add .
git status   # vérifie ce qui sera commité (les fichiers ignorés par .gitignore n'apparaissent pas)
git commit -m "Première version : devoir de réassurance XL MTPL — pricing complet"
```

## 3. Lier au dépôt distant et pousser

Remplace l'URL ci-dessous par celle que GitHub t'a affichée à l'étape 1 :
```bash
git remote add origin https://github.com/<ton-username>/reassurance-xl-mtpl-pricing.git
git push -u origin main
```

GitHub te demandera de t'authentifier :
- Soit avec ton login + un **Personal Access Token** (recommandé — créer un
  token sur https://github.com/settings/tokens/new avec le scope `repo`).
- Soit via GitHub Desktop / GitHub CLI (`gh auth login`) si tu les as installés.

## 4. Vérifier

Recharge la page de ton repo dans le navigateur. Tu devrais voir :
- `README.md` rendu en page d'accueil avec les résultats clés.
- Les dossiers `code/`, `figures/`, `outputs/`.
- **PAS** le PDF du cours (60 MB, exclu par `.gitignore`), **PAS** le classeur
  source cédante, **PAS** les CSV intermédiaires.

## 5. Mises à jour ultérieures

Pour pousser une nouvelle version du travail :
```bash
git add .
git commit -m "Description courte des modifications"
git push
```

## En cas de problème

- **« fatal: not a git repository »** : tu n'es pas dans le bon dossier — fais
  d'abord `cd C:\Users\etudiant\Documents\Claude\Projects\reassurance`.
- **« Authentication failed »** : ton mot de passe GitHub ne fonctionne plus
  via la ligne de commande depuis 2021. Utilise un Personal Access Token
  (lien ci-dessus) à la place du mot de passe.
- **Fichier trop gros** : si jamais GitHub refuse un fichier de plus de 100 MB,
  ajoute son chemin à `.gitignore`, puis fais `git rm --cached <chemin>` avant
  de recommiter.
