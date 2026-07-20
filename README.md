# Smart Academy Manager

Smart Academy Manager est une plateforme de gestion academique et RH construite avec Angular, Django REST Framework et PostgreSQL.

Le projet fournit une fondation technique et plusieurs workflows metier complets :

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

Le frontend Angular contient l'authentification, les espaces par rôle, le recrutement, les Business Units, les offres, la gestion des utilisateurs et le workflow complet des formations.

## Modules actuellement disponibles

- authentification JWT, profil et changement de mot de passe ;
- candidatures, documents, entretiens et conversion en stagiaire/collaborateur ;
- offres rattachées aux Business Units ;
- Business Units, membres et besoins ;
- catalogue de formations et gestion des sessions ;
- demandes d'inscription, validation Manager puis Super Admin et historique ;
- gestion des stages : affectations, dates, progression, documents et évaluations ;
- gestion des projets : affectations collaborateurs/stagiaires, livrables, progression, commentaires et documents ;
- vues dédiées Formateur/Tuteur et Client externe ;
- documentation OpenAPI/Swagger.

## Prochaine etape

Suis le guide [backend/README.md](backend/README.md) pour creer l'environnement Python, installer les dependances, creer la base PostgreSQL et lancer les migrations.
