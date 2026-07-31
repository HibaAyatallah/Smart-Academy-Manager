# Rapport d'avancement — Smart Academy Manager

**Date de l'audit :** 31 juillet 2026  
**Périmètre :** état réel du workspace (y compris les modifications non commitées)  
**Méthode :** lecture du code, des routes Angular et Django, des services HTTP, des rôles et permissions, puis exécution des builds, checks et suites de tests.

## 1. Synthèse

### Avancement global estimé : **70 %**

Le socle métier principal est largement implémenté et techniquement sain : le frontend compile, les 129 tests Angular passent, les 173 tests Django passent, les migrations sont cohérentes et les rôles sont contrôlés à la fois dans Angular et dans DRF. Le projet n'est toutefois pas prêt pour la production : il manque l'infrastructure de déploiement/CI, les tests de bout en bout, plusieurs écrans frontend, le Data Warehouse/ETL et les fonctions IA prévues.

| Axe | Poids | État estimé | Contribution |
|---|---:|---:|---:|
| Backend Django/DRF | 20 % | 94 % | 18,8 |
| Frontend Angular | 15 % | 86 % | 12,9 |
| Connexion frontend/backend | 15 % | 89 % | 13,4 |
| Rôles, permissions et sécurité | 10 % | 88 % | 8,8 |
| Tests et qualité | 15 % | 92 % | 13,8 |
| Déploiement et exploitation | 10 % | 12 % | 1,2 |
| Data Warehouse / ETL | 10 % | 0 % | 0 |
| Fonctions IA | 5 % | 0 % | 0 |
| **Total** | **100 %** |  | **68,9 %, arrondi à 70 %** |

Cette estimation mesure le périmètre final documenté. Si l'on ne considère que l'application de gestion actuelle, hors Data Warehouse, IA et industrialisation, son avancement fonctionnel est plutôt de l'ordre de **88–90 %**.

## 2. Résultats de validation

| Vérification exécutée | Résultat |
|---|---|
| `npm.cmd run build` | **Succès**, bundle production généré, 0 erreur et 0 avertissement de budget |
| `npm.cmd test -- --watch=false --browsers=ChromeHeadless` | **129/129 tests réussis** |
| `manage.py check` | **0 problème** |
| `manage.py makemigrations --check --dry-run` | **Aucune migration manquante** |
| `manage.py test --keepdb` | **173/173 tests réussis** en 257,7 s |
| `manage.py check --deploy --settings=config.settings.production` | **44 avertissements** : 43 liés surtout au schéma OpenAPI, 1 avertissement sécurité sur la redirection HTTPS |

La première exécution Django sans `--keepdb` a trouvé `test_smart_academy_db` déjà présente et a demandé une confirmation impossible en mode non interactif. Ce n'est pas un échec du code ; la suite complète passe avec `--keepdb`. Cela révèle néanmoins que la procédure de test/CI n'est pas encore robuste.

Les tests Angular réussissent mais émettent deux avertissements « spec has no expectations » (`TrainingService` client et navigation `MainLayout`) et des messages console d'échec d'authentification produits volontairement par les tests négatifs.

## 3. Fonctionnalités terminées

### Socle et authentification

- Modèle utilisateur personnalisé avec 8 rôles cohérents entre Django et Angular : `SUPER_ADMIN`, `HR`, `BU_MANAGER`, `TRAINER_TUTOR`, `EMPLOYEE`, `INTERN`, `CANDIDATE`, `CLIENT`.
- Authentification JWT, rafraîchissement et vérification de jeton, profil courant et changement de mot de passe.
- Guards Angular d'authentification et de rôle, redirection vers le dashboard propre à chaque rôle.
- Gestion des utilisateurs réservée au Super Admin, avec import CSV/XLSX en prévisualisation puis confirmation.

### Recrutement et stages

- CRUD et cycle de vie des offres : brouillon, publication, fermeture et archivage.
- Dépôt public de candidature avec profil candidat, documents et limitation de débit.
- Consultation des candidatures du candidat.
- Workflow de traitement des candidatures : revue, présélection, entretien, acceptation et rejet.
- Conversion vers un dossier stagiaire, documents, validation et évaluations.
- Vues RH en lecture seule sur les stagiaires acceptés et les collaborateurs par BU.
- Commande d'anonymisation des candidatures arrivées à expiration.

### Business Units

- CRUD des BU, adhésions et besoins.
- Filtrage par périmètre du manager et protection contre la réaffectation non autorisée.
- Historique d'adhésion et possibilité de réintégration après désactivation.
- Workflow des besoins et choix des destinataires de formation.
- Écrans Angular de liste, détail, membres, besoins et formations de la BU.

### Formations

- Catalogue, sessions, inscriptions et décisions manager/Super Admin.
- Accès distinct pour le client.
- Présences, historique, validation et certificats.
- Règles de lecture/écriture par rôle et filtrage des données.
- Moodle a été retiré du périmètre et du code.

### Projets, rapports et backend de notifications

- Projets, affectations, livrables, commentaires et documents.
- Rapports synthétiques, dashboard RH et exports CSV/PDF.
- Notifications, préférences, marquage lu/non lu et journal d'audit côté API.
- Documentation API Swagger/ReDoc disponible.

## 4. Fonctionnalités en cours ou partielles

| Fonctionnalité | État constaté |
|---|---|
| Notifications et audit frontend | Les modèles et le service Angular existent, mais les composants `notification-center` et `audit-log` sont supprimés dans le worktree. Le bouton de cloche du layout n'a pas d'action. |
| Rapports frontend | `ReportService` existe et alimente notamment les dashboards, mais il n'existe pas d'espace analytique complet et routé dédié aux rapports/exports. |
| Pages publiques | Accueil, groupe, recrutement, contact, confidentialité et mentions légales sont présents ; certains contenus restent essentiellement statiques et le formulaire de contact n'est relié à aucune API visible. |
| Dashboard | Décliné par rôle et connecté aux données disponibles, mais pas encore un tableau de bord analytique complet. |
| Tests frontend | Bonne couverture des services/guards et des flux importants, mais plusieurs composants métiers n'ont pas de spec dédiée et deux specs ne contiennent aucune assertion. |
| Documentation OpenAPI | Accessible, mais incomplète : serializers/types non résolus et certaines APIViews ignorées lors de la génération. |
| Configuration de production | HSTS, cookies sécurisés, `DEBUG=False` et secret obligatoire sont configurés ; la redirection HTTPS et le reverse proxy restent à mettre en place. |

## 5. Fonctionnalités non commencées

- Data Warehouse, schéma dimensionnel, historique analytique et pipelines ETL.
- Fonctions IA prévues : extraction de CV, recommandation de formations, analyse des écarts de compétences et matching candidat–offre.
- Tests end-to-end réels Angular ↔ Django avec navigateur et base de données.
- Pipeline CI/CD.
- Conteneurisation Docker et orchestration PostgreSQL/Django/frontend.
- Configuration de reverse proxy et procédure de déploiement reproductible.
- Supervision, métriques, alertes, sauvegarde/restauration et stratégie de stockage des médias.

Le SSO et Moodle sont considérés hors périmètre, donc ne sont pas comptés comme manquants.

## 6. État du frontend Angular

**État : fonctionnel et compilable, mais incomplet sur quelques parcours.**

- Angular 21, composants standalone, lazy loading et Angular Material.
- Routes publiques, authentification et espace privé protégés correctement.
- Les 8 dashboards de rôle sont enregistrés ; navigation et routes utilisent les mêmes identifiants de rôle que le backend.
- Les services utilisent `environment.apiBaseUrl` sans double slash ; le défaut historique `/api//offers/` est corrigé.
- En développement, l'URL est `http://127.0.0.1:8001/api/`. En production, le contrat est `/api/`, ce qui exige un reverse proxy absent du dépôt.
- Les jetons access et refresh sont stockés dans `localStorage`, ce qui augmente l'impact potentiel d'une faille XSS.
- Le build production initialise 448,86 kB bruts, sous la limite d'avertissement de 500 kB.
- Plusieurs chaînes affichées dans la sortie PowerShell montrent du mojibake (`dâ€™ensemble`, `PrÃ©sences`). Il faut vérifier l'encodage réel dans le navigateur et normaliser les fichiers en UTF-8.

## 7. État du backend Django/DRF

**État : mature, testé et cohérent au niveau des migrations.**

- Django 5.2, DRF 3.16, SimpleJWT, django-filter, drf-spectacular et PostgreSQL.
- 8 applications installées : accounts, recruitment, business_units, trainings, projects, notifications, reports et core.
- Les routes couvrent l'authentification, utilisateurs/import, offres/candidatures/entretiens/stages, BU, formations/inscriptions/présences/certificats, projets, notifications/audit et rapports.
- Permission globale `IsAuthenticated`, avec exceptions explicites et limitées pour la lecture des offres publiées et le dépôt public de candidature.
- Throttling global et throttles spécifiques pour login et dépôt public.
- Les querysets et permissions de domaine limitent l'accès aux participants, propriétaires, managers ou rôles autorisés.
- Les 173 tests passent et aucune migration n'est en attente.

Point faible notable : la génération du schéma OpenAPI signale des querysets qui supposent un utilisateur authentifié, des types de `SerializerMethodField` non documentés, des collisions d'enums et cinq APIViews sans serializer déductible. L'API fonctionne, mais son contrat généré n'est pas totalement fiable.

## 8. Connexion frontend–backend

**État : correctement câblée au niveau code, partiellement validée en intégration.**

- Les chemins des services Angular correspondent aux routeurs DRF : `/users/`, `/offers/`, `/applications/`, `/business-units/`, `/trainings/`, `/enrollments/`, `/attendance/`, `/projects/`, `/notifications/`, `/reports/`, etc.
- L'intercepteur ajoute le bearer token et le service d'authentification sait rafraîchir la session.
- CORS et CSRF autorisent les origines locales Angular ; le backend local écoute selon la documentation sur le port 8001.
- Les contrats principaux sont testés isolément par `HttpTestingController` et par les tests API Django.
- Il n'existe cependant aucun test e2e qui démarre les deux applications et vérifie un parcours complet avec PostgreSQL. La connexion est donc **fortement étayée**, mais pas certifiée de bout en bout.
- La production repose sur un proxy `/api/` non fourni. Sans configuration d'hébergement supplémentaire, le frontend produit ne pourra pas joindre Django.

## 9. Rôles et permissions

| Rôle | Accès principal vérifié | Restrictions principales |
|---|---|---|
| Super Admin | Administration complète, utilisateurs, recrutement, BU, formations, audit | Aucun accès métier majeur manquant |
| HR | Stagiaires acceptés, collaborateurs par BU, formations et dashboard RH en lecture | Méthodes non sûres refusées ; pas de gestion utilisateurs/recrutement |
| BU Manager | Membres et besoins de sa BU, validations d'inscriptions, stagiaires de son périmètre | Périmètre BU et champs sensibles protégés |
| Formateur/Tuteur | Formations opérationnelles, présences, certificats selon règles | Pas d'administration globale |
| Employé | Formations, demandes d'inscription, projets autorisés, stagiaires selon participation | Accès limité à ses données/participations |
| Stagiaire | Son stage, formations et projets assignés | Pas d'accès global |
| Candidat | Offres publiées et ses candidatures | Pas d'accès aux candidatures d'autrui |
| Client | Endpoints et écrans de formations client isolés | Exclu du catalogue interne |

Le contrôle Angular améliore l'UX mais n'est pas considéré comme une barrière de sécurité ; les protections décisives sont bien présentes côté DRF. Les tests backend comprennent des cas de séparation de rôles et d'accès objet.

## 10. Erreurs, lacunes et risques de sécurité

### Critiques / élevées

1. **Absence d'industrialisation de production.** Aucun Dockerfile, docker-compose, workflow CI, proxy nginx/équivalent ni configuration de déploiement n'est présent.
2. **Pas de test e2e.** Les tests unitaires/API peuvent passer tout en laissant subsister une rupture de contrat ou de déploiement.
3. **Écrans Notifications/Audit absents.** Le backend et le service existent, mais le parcours utilisateur est actuellement interrompu.

### Moyennes

4. **Jetons JWT dans `localStorage`.** Un XSS permettrait leur exfiltration. Préférer un refresh token en cookie HttpOnly/Secure/SameSite avec rotation et blacklist.
5. **`SECURE_SSL_REDIRECT` absent.** `check --deploy` émet `security.W008`. La redirection doit être assurée par Django ou explicitement garantie par le proxy.
6. **Schéma OpenAPI dégradé.** 43 avertissements drf-spectacular, notamment des endpoints ignorés et des erreurs sur `AnonymousUser`.
7. **Uploads à durcir.** Les candidatures ont des validateurs de taille/type, mais tous les autres `FileField` (projets, formations, certificats, documents de stage) doivent être audités de manière uniforme : MIME réel, extension, antivirus, nom aléatoire, stockage privé et autorisation au téléchargement.
8. **Pas de rotation/blacklist JWT visible.** La durée courte de l'access token limite le risque, mais un refresh token volé reste valable jusqu'à expiration.
9. **Base de test persistante et exécution lente.** La suite nécessite actuellement `--keepdb` dans cet environnement et prend plus de quatre minutes ; la CI devra provisionner une base isolée automatiquement.

### Faibles / qualité

10. Deux tests Angular réussissent sans assertion.
11. Messages `console.error` attendus dans les tests, ce qui rend les vraies erreurs plus difficiles à repérer.
12. Possibles chaînes mojibake dans le code/navigation.
13. Pas de mesure de couverture publiée ni de seuil de couverture.
14. Worktree très chargé : nombreuses modifications et suppressions non commitées, rapports et sorties de build non suivis. Cela augmente le risque de perdre ou mélanger des changements.
15. Le fallback de secret faible existe dans `base.py`, mais `production.py` redéfinit correctement `SECRET_KEY` sans valeur par défaut. Le risque porte donc surtout sur un lancement accidentel avec les settings de base/local en environnement exposé.
16. Le fichier local `backend/.env` contient un secret réel mais n'est pas suivi par Git. Il doit rester ignoré et être remplacé s'il a déjà été partagé ailleurs.

## 11. Prochaines tâches par priorité

### P0 — Rendre l'état actuel livrable

1. Restaurer ou réimplémenter les écrans Notifications, préférences et Audit, relier la cloche du header et ajouter les routes/permissions Angular.
2. Ajouter un test e2e minimal des parcours critiques : login/refresh, candidature publique, traitement Super Admin, besoin BU, inscription formation et projet.
3. Corriger les 44 avertissements de `check --deploy`/drf-spectacular : `SECURE_SSL_REDIRECT` ou garantie proxy documentée, `swagger_fake_view`, serializers explicites, types de champs calculés et noms d'enums.
4. Stabiliser le worktree : sélectionner les changements voulus, retirer les artefacts temporaires du périmètre versionné et créer une baseline reproductible.

### P1 — Production et sécurité

5. Fournir Dockerfiles, composition PostgreSQL/backend/frontend, reverse proxy `/api/` et stockage persistant des médias.
6. Créer une CI qui exécute build Angular, 129 tests frontend, checks/migrations et 173 tests backend sur une base éphémère.
7. Durcir l'authentification : cookie HttpOnly pour le refresh token, rotation/blacklist, CSP stricte et revue XSS.
8. Uniformiser la sécurité des uploads et servir tous les documents privés via des endpoints autorisés, pas directement depuis `MEDIA_URL`.
9. Ajouter journalisation structurée, suivi d'erreurs, sauvegardes PostgreSQL/médias et procédure de restauration.

### P2 — Compléter le produit courant

10. Créer un espace Rapports/Exports réellement routé et accessible aux seuls rôles autorisés.
11. Relier le formulaire Contact à un backend ou retirer l'illusion d'envoi.
12. Compléter les specs sans assertions, ajouter des tests aux composants non couverts et publier la couverture avec seuils.
13. Vérifier et corriger l'encodage UTF-8/mojibake et effectuer une revue d'accessibilité responsive.
14. Documenter une matrice exhaustive endpoint × méthode × rôle et la couvrir par des tests paramétrés.

### P3 — Analytics et IA

15. Concevoir le Data Warehouse, les dimensions/faits, la conservation et les pipelines ETL idempotents.
16. Construire les KPI analytiques et dashboards décisionnels.
17. Implémenter ensuite l'extraction de CV, les recommandations de formation et le matching candidat–offre comme aide à la décision, avec traçabilité et validation humaine.

## 12. Verdict

Smart Academy Manager est un **MVP avancé et techniquement crédible**. Les fonctions de gestion essentielles sont présentes, les rôles sont sérieusement séparés et les deux suites de tests sont vertes. Le frein principal n'est plus le CRUD métier, mais la finition de quelques parcours frontend, la preuve e2e, la qualité du contrat OpenAPI et surtout l'industrialisation/sécurisation de la production. Le pourcentage global raisonnable à retenir dans l'état actuel est **70 %**.
