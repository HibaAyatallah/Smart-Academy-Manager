# Smart Academy Manager

Smart Academy Manager est une plateforme de gestion academique et RH construite avec Angular, Django REST Framework et PostgreSQL.

Cette premiere etape met en place uniquement la fondation technique :

- backend Django structure et evolutif ;
- PostgreSQL configure via variables d'environnement ;
- utilisateur personnalise avec roles metier ;
- authentification JWT ;
- permissions de base ;
- documentation OpenAPI/Swagger ;
- depot Git local initialise.

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
  docs/
```

Le frontend Angular sera ajoute dans une etape separee, apres validation du backend.

## Prochaine etape

Suis le guide [backend/README.md](backend/README.md) pour creer l'environnement Python, installer les dependances, creer la base PostgreSQL et lancer les migrations.

