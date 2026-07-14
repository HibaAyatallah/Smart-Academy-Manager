# Smart Academy Manager Backend

Backend Django REST Framework pour Smart Academy Manager.

## Contenu de cette fondation

- projet Django structure autour de `config` ;
- applications internes dans `apps` ;
- utilisateur personnalise base sur l'email ;
- roles metier centralises ;
- permissions DRF de base ;
- authentification JWT avec Simple JWT ;
- documentation API avec drf-spectacular ;
- configuration PostgreSQL via `.env`.

## Installation locale

Les etapes manuelles sont detaillees dans [../docs/backend-setup.md](../docs/backend-setup.md).

Resume des commandes principales, a executer dans ce dossier :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\local.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Documentation API

Apres lancement du serveur :

- Swagger UI : http://127.0.0.1:8000/api/docs/
- ReDoc : http://127.0.0.1:8000/api/redoc/
- Schema OpenAPI : http://127.0.0.1:8000/api/schema/

## Tests

Les tests de fondation couvrent le modele utilisateur, le JWT, le profil connecte et les permissions de gestion des utilisateurs.

Dans PowerShell, depuis ce dossier :

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py test
```

Avec PostgreSQL, l'utilisateur de base de donnees doit pouvoir creer une base de test en local. Si la commande echoue avec une erreur de creation de base, execute avec un compte PostgreSQL administrateur :

```powershell
psql -U postgres -c "ALTER USER smart_academy_user CREATEDB;"
```

Ce droit est utile pour le developpement et les tests locaux. Il n'est pas destine a un utilisateur applicatif de production.

## Candidatures

Le module de candidatures ajoute :

- depot public de candidature ;
- gestion RH des statuts ;
- documents de candidature ;
- entretiens ;
- historique des statuts ;
- transformation d'un candidat accepte en stagiaire ou collaborateur ;
- refus avec desactivation du compte ;
- anonymisation des candidatures expirees.

Commande d'anonymisation :

```powershell
python manage.py anonymize_expired_applications
```
