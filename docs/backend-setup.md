# Backend setup

Ce document liste les actions manuelles a effectuer dans PowerShell pour lancer le backend Django avec PostgreSQL.

## 1. Ouvrir le bon dossier

```powershell
cd C:\Users\hibaa\OneDrive\Desktop\Smart_Academy_Manager\backend
```

## 2. Creer et activer l'environnement virtuel Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Verification :

```powershell
python --version
pip --version
```

## 3. Installer les dependances Python

Dans le meme terminal PowerShell, toujours dans le dossier `backend` :

```powershell
pip install -r requirements\local.txt
```

Verification :

```powershell
python -m django --version
```

## 4. Creer la base PostgreSQL

Ouvre un nouveau terminal PowerShell et lance :

```powershell
psql -U postgres
```

Dans le shell PostgreSQL, execute :

```sql
CREATE DATABASE smart_academy_db;
CREATE USER smart_academy_user WITH PASSWORD 'change_this_password';
ALTER ROLE smart_academy_user SET client_encoding TO 'utf8';
ALTER ROLE smart_academy_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE smart_academy_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE smart_academy_db TO smart_academy_user;
\c smart_academy_db
GRANT CREATE ON SCHEMA public TO smart_academy_user;
```

Verification :

```sql
\l
\du
\q
```

Remplace ensuite `change_this_password` dans ton fichier `.env`.

## 5. Creer le fichier d'environnement

Dans PowerShell, dans le dossier `backend` :

```powershell
Copy-Item .env.example .env
notepad .env
```

Modifie au minimum :

```text
DJANGO_SECRET_KEY=une-cle-secrete-longue
DATABASE_URL=postgres://smart_academy_user:change_this_password@localhost:5432/smart_academy_db
```

## 6. Lancer les migrations et creer le super administrateur

Dans PowerShell, dans le dossier `backend`, avec l'environnement virtuel active :

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Le super utilisateur cree par la commande aura le role `SUPER_ADMIN` automatiquement.

## 7. Lancer le serveur

```powershell
python manage.py runserver
```

Verification dans le navigateur :

- API root : http://127.0.0.1:8000/api/
- Swagger : http://127.0.0.1:8000/api/docs/
- Schema OpenAPI : http://127.0.0.1:8000/api/schema/

