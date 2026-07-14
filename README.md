# Smart Academy Manager

Smart Academy Manager est une plateforme de gestion academique et RH construite avec Angular, Django REST Framework et PostgreSQL.

Cette premiere etape met en place uniquement la fondation technique :

- backend Django structure et evolutif ;
- PostgreSQL configure via variables d'environnement ;
- utilisateur personnalise avec roles metier ;
- authentification JWT ;
- permissions de base ;
- documentation OpenAPI/Swagger ;
- depot Git local initialise ;
- module de gestion des candidatures.

## Architecture cible

```text
Smart_Academy_Manager/
  backend/
    apps/
      accounts/
      core/
    config/
      settings/
    requirements/
  frontend/
    src/
      app/
        core/
        features/
        layouts/
        shared/
  docs/
```

Le frontend Angular contient maintenant l'authentification, les dashboards et le module candidatures.

## Prochaine etape

Suis le guide [backend/README.md](backend/README.md) pour creer l'environnement Python, installer les dependances, creer la base PostgreSQL et lancer les migrations.
