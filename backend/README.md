# Backend — Smart Academy Manager

Le backend fournit l’API REST, la persistance des données, les règles métier, les permissions et les traitements d’analyse de Smart Academy Manager. Il repose sur **Django**, **Django REST Framework** et **PostgreSQL**.

## Principaux modules

- `accounts` : utilisateurs, profils, rôles et authentification JWT ;
- `business_units` : Business Units, membres et besoins ;
- `recruitment` : offres, candidatures, documents, entretiens et analyse des CV ;
- `trainings` : formations, inscriptions, présences et certificats ;
- `projects` : projets, affectations et livrables ;
- `notifications` : notifications, e-mails et audit ;
- `reports` et `analytics` : indicateurs, exports et entrepôt analytique ;
- `assistant` : assistant Ollama sécurisé par le contexte de l’utilisateur.

L’API utilise Django REST Framework, JWT SimpleJWT et des permissions par rôle. La documentation OpenAPI est exposée par les routes configurées dans le projet.

L’analyse des CV accepte les PDF textuels et DOCX jusqu’à 5 Mo. Le texte est extrait avec PyMuPDF ou python-docx, puis structuré avant le matching avec les offres et la génération de recommandations. Une validation humaine reste nécessaire.

## Configuration

Copier `.env.example` vers `.env`, puis configurer au minimum :

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DB_ENGINE=postgresql
DB_NAME=smart_academy_db
DB_USER=smart_academy_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

Les paramètres SMTP, CORS, limites d’envoi et la connexion Ollama sont également configurables dans ce fichier.

## Installation et lancement

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver 8001
```

Commandes utiles :

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
python manage.py check
```
