# Smart Academy Manager

Smart Academy Manager est une plateforme web de gestion académique et RH réalisée dans le cadre d’un **stage chez FINATECH** par **Hiba Ayatallah**.

Le projet centralise les parcours de recrutement, l’intégration et le suivi des stagiaires et collaborateurs, les formations, les projets et le pilotage des activités. Il propose des espaces adaptés aux différents profils et sécurise l’accès aux données selon le rôle et la Business Unit.

## Fonctionnalités principales

- authentification JWT, profils, rôles et permissions ;
- gestion des utilisateurs, Business Units, membres et besoins ;
- offres, candidatures, entretiens et conversion en stagiaire ou collaborateur ;
- extraction structurée des CV PDF/DOCX avec OCR optionnel, matching explicable, synthèse et classement par offre ;
- gestion des stages, projets, livrables et évaluations ;
- formations, inscriptions, présences et certificats PDF ;
- tableaux de bord, rapports, exports, notifications et journal d’audit ;
- assistant métier Ollama avec historique privé et contexte filtré par utilisateur.

## Architecture

- **Frontend** : Angular, Angular Material et interface responsive.
- **Backend** : Django et Django REST Framework, exposant une API REST.
- **Base de données** : MySQL 8 avec `utf8mb4`.
- **Sécurité** : authentification JWT, guards Angular et permissions backend.
- **IA** : analyse des CV, matching, recommandations et assistant local Ollama.

Les rôles principaux sont : Super Administrateur, RH, Responsable Business Unit, Collaborateur, Stagiaire, Candidat, Formateur/Tuteur et Client.

## Structure du projet

```text
Smart_Academy_Manager/
├── backend/        API Django, modèles, règles métier et tests
├── frontend/       application Angular
├── deploy/         fichiers de déploiement
├── scripts/        sauvegarde, restauration et déploiement
└── docker-compose.yml
```

## Lancement rapide

Prérequis : Python 3.12+, Node.js/npm et MySQL 8. Copier les exemples d’environnement, puis renseigner les secrets et la connexion à la base.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver 8001
```

Dans un autre terminal :

```powershell
cd frontend
npm install
npm start
```

L’interface est disponible sur `http://localhost:4200` et l’API sur `http://localhost:8001/api/`.

## Technologies principales

Angular, TypeScript, Angular Material, Django, Django REST Framework, MySQL, SimpleJWT, PyMuPDF, python-docx, Ollama, Docker et Nginx.

## État final

Le projet est stabilisé pour la démonstration et la livraison académique. Les suites automatisées backend et frontend ainsi que le build Angular de production sont validés. Une mise en production reste conditionnée à la fourniture des secrets, de MySQL 8, du SMTP, du stockage persistant des médias et, pour l’assistant, d’un service Ollama configuré.

Le rapport de clôture complet, la matrice d’état et les résultats de validation se trouvent dans [`FINAL_PROJECT_REPORT.md`](FINAL_PROJECT_REPORT.md).

La frontière technique entre parsing, règles, OCR, scoring et Ollama est documentée dans [`AI_RECRUITMENT.md`](AI_RECRUITMENT.md).

### Données de démonstration

Après les migrations, créez ou rafraîchissez le jeu synthétique sans supprimer les données existantes :

```bash
cd backend
python manage.py seed_demo --password "<mot-de-passe-temporaire-de-12-caracteres-minimum>"
```

La commande est idempotente, utilise uniquement les domaines réservés `example.test`, couvre les huit rôles et les principaux workflows (BU, recrutement, conversion stagiaire, analyse/matching CV, formation, présence, certificat, projet, notification et audit). Ne réutilisez jamais ce mot de passe en production.
