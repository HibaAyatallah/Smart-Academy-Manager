# Premier push GitHub

## 1. Verifier les fichiers suivis

Dans PowerShell :

```powershell
cd C:\Users\hibaa\OneDrive\Desktop\Smart_Academy_Manager
git status --short --ignored
```

Les fichiers suivants doivent rester ignores :

- `backend/.env`
- `backend/.venv/`
- `__pycache__/`

## 2. Lancer les controles backend

Dans PowerShell :

```powershell
cd C:\Users\hibaa\OneDrive\Desktop\Smart_Academy_Manager\backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Si les tests echouent avec une erreur PostgreSQL de creation de base de test, donne le droit de creation de base a l'utilisateur local de developpement :

```powershell
psql -U postgres -c "ALTER USER smart_academy_user CREATEDB;"
```

Puis relance :

```powershell
python manage.py test
```

Ce droit est utile pour les tests locaux, pas pour un utilisateur applicatif de production.

## 3. Creer le premier commit

Dans PowerShell :

```powershell
cd C:\Users\hibaa\OneDrive\Desktop\Smart_Academy_Manager
git add .
git commit -m "Initial backend foundation"
```

## 4. Lier GitHub et pousser

Cree d'abord un depot vide sur GitHub, sans README, sans `.gitignore` et sans licence.

Ensuite, dans PowerShell :

```powershell
git remote add origin https://github.com/<ton-compte>/<ton-depot>.git
git push -u origin main
```

Verification :

```powershell
git remote -v
git status
```
