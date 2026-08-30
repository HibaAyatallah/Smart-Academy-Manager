# Rapport final de stabilisation — Smart Academy Manager

**Date de clôture :** 27 août 2026
**Référence auditée :** branche `main`, commit de départ `e542506`
**Verdict :** **READY WITH LIMITATIONS — prêt pour démonstration et livraison académique, pas déclaré déployé en production**

> **Mise à jour base de données — 30 août 2026 :** la base définitive est
> MySQL 8 avec `utf8mb4`. La chaîne complète de 75 migrations, la restauration
> de 742 objets et les 294 tests backend ont été validés sur MySQL. PostgreSQL
> et ses sauvegardes sont conservés uniquement comme source historique et
> solution de retour arrière.

## 1. Résumé de stabilisation

L'audit final a couvert le backend Django/DRF, le frontend Angular, les contrats API, les migrations, les rôles, la sécurité, l'analyse de CV, l'assistant, les rapports, ainsi que les configurations Docker, cPanel et CI. La base applicative était déjà solide : 279 tests Django et 172 tests Angular passent, aucune migration modèle n'est manquante et le bundle Angular de production est généré.

Deux blocages de déploiement ont été corrigés : les variables obligatoires de sécurité manquaient au job CI exécutant les settings de production, et l'image backend ne créait pas le répertoire utilisé par le journal de production. Le modèle d'environnement racine a aussi été complété sans secret. Aucun refactoring d'architecture ni ajout fonctionnel n'a été réalisé.

Le système est stable pour une démonstration réaliste et une remise académique. La qualification « production-ready » ne peut pas être accordée sans validation sur l'infrastructure cible, MySQL persistant, HTTPS, SMTP, sauvegardes restaurées et supervision. Ollama reste une dépendance externe facultative pour l'assistant.

## A. Vue d'ensemble du projet

Smart Academy Manager est une plateforme web réalisée dans le contexte d'un stage chez FINATECH. Le problème initial était la dispersion des activités de recrutement, d'intégration, de formation, de suivi des stages et projets, avec peu de visibilité transversale et des droits difficiles à maîtriser.

Les objectifs étaient de centraliser les parcours RH et académiques, structurer les Business Units (BU), automatiser les tâches répétitives, sécuriser les accès, fournir des indicateurs et proposer une aide raisonnable à l'exploitation des CV. Les utilisateurs visés sont les super-administrateurs, RH, responsables de BU, formateurs/tuteurs, collaborateurs, stagiaires, candidats et clients externes.

La solution finale est une application Angular responsive consommant une API REST Django. Django porte les règles métier et les permissions, MySQL 8 est la base cible, JWT gère les sessions API, et des traitements locaux extraient et rapprochent les informations de CV. Un assistant Ollama optionnel exploite un contexte filtré par utilisateur.

## B. Architecture initiale et finale

Le projet a démarré avec les choix structurants suivants :

- **Angular et Angular Material** pour une SPA typée, des formulaires réactifs, une navigation par rôles et des composants UI cohérents ;
- **Django** pour les modèles, migrations, validations, administration et règles métier ;
- **Django REST Framework** pour les ViewSets, serializers, permissions, pagination et endpoints REST ;
- **MySQL 8 avec utf8mb4** comme base relationnelle principale ;
- **SimpleJWT** pour les jetons d'accès et de rafraîchissement.

Le navigateur charge l'application Angular. Les services Angular appellent `/api/`; l'intercepteur ajoute le jeton Bearer et tente une rotation contrôlée du jeton expiré. Les guards améliorent l'expérience en empêchant l'ouverture de routes non autorisées, mais l'autorité de sécurité reste côté Django. Les serializers valident les entrées, les ViewSets appliquent les permissions et transactions, puis l'ORM persiste les données dans MySQL. En Docker, Nginx sert Angular et relaie `/api/` et `/media/` vers Gunicorn/Django.

## C. Évolution chronologique

### 1. Socle backend

Le premier jalon a créé le projet Django, le modèle utilisateur personnalisé, les rôles, JWT, les serializers, les premiers tests et la séparation des settings local/production. Ce choix précoce a évité d'ajouter tardivement un modèle utilisateur incompatible avec les migrations.

### 2. Recruitment, Business Units et frontend initial

Les offres, candidats, candidatures, entretiens, documents et règles de transition ont été ajoutés, puis les BU, adhésions et besoins. Angular a été introduit avec layouts public/authentifié, pages publiques, formulaires, services HTTP, guards et modèles TypeScript. La difficulté principale était l'alignement des statuts, types et permissions entre frontend et backend ; les contrats typés et les tests d'API/composants ont servi de garde-fous.

### 3. Navigation, profils et besoins BU

Les routes ont été stabilisées, les tableaux de bord par rôle ont été introduits et le workflow des besoins BU a gagné ses formulaires, historiques et décisions. La navigation a été rendue dépendante du rôle pour ne présenter que les workflows autorisés.

### 4. Formations

Le domaine formation a ajouté catalogues, sessions, inscriptions, validations manager/formateur, présences quotidiennes, historique et certificats. Les vues client en lecture seule et les périmètres BU ont été séparés des fonctions d'administration.

### 5. Stages et projets

Les candidatures acceptées peuvent alimenter un profil de stagiaire. Le suivi comprend documents requis, dépôt et validation, évaluations, tuteur/BU et statut de stage. Le module projets gère projets, affectations, livrables, commentaires et documents avec accès limité aux participants et administrateurs.

### 6. Notifications, e-mails et audit

Des notifications privées, préférences, signaux, traces de livraison e-mail, middleware d'audit et journaux sensibles ont été ajoutés. Les échecs SMTP sont journalisés et testés sans rendre les données d'un autre utilisateur accessibles.

### 7. Rapports, KPI et analytique

Des résumés et tableaux de bord par rôle/BU, exports CSV/XLSX/PDF et un petit schéma analytique (dimensions/faits) synchronisable ont été introduits. Les requêtes sont filtrées selon le rôle avant agrégation.

### 8. Analyse de CV et assistant

L'extraction PDF/DOCX, la structuration des coordonnées, compétences, langues, études et expériences, le matching offre/candidature et les recommandations de formation ont été renforcés. L'assistant Ollama a été isolé derrière un provider, limité, historisé par conversation et alimenté par un contexte autorisé.

### 9. Sécurité, ergonomie et déploiement

La séparation RH/Super Admin a été durcie, le reset de mot de passe sécurisé a été ajouté, les menus ont été alignés sur les autorisations et les écrans responsive améliorés. Docker/Nginx, cPanel/Passenger, CI MySQL et scripts de sauvegarde/restauration ont ensuite été ajoutés. La phase finale a validé ces éléments et corrigé les deux défauts de configuration décrits dans la section M.

## D. Rôles réellement implémentés

| Rôle | Portée finale |
|---|---|
| Super Admin | Administration complète : utilisateurs, BU, recrutement, transitions/conversions, formations, rapports, audit et opérations sensibles. |
| RH (`HR`) | Lecture globale mais restreinte : stagiaires acceptés, collaborateurs par BU, formations/sessions et tableaux RH. Les mutations administratives lui sont refusées. |
| Responsable BU (`BU_MANAGER`) | Données de sa BU, membres, création/suivi des besoins, stages de son périmètre, validations de formation et présence selon le workflow. |
| Formateur/Tuteur (`TRAINER_TUTOR`) | Catalogues/sessions autorisés, inscriptions, présences et suivi pédagogique prévu par les permissions. |
| Collaborateur (`EMPLOYEE`) | Profil, notifications, formations de sa BU et projets dont il est participant ; création/interaction projet selon le workflow existant. |
| Stagiaire (`INTERN`) | Espace de stage personnel, documents et informations explicitement exposés à son compte. |
| Candidat (`CANDIDATE`) | Profil/candidatures propres et espace CV. Le dépôt public reste possible via les endpoints explicitement publics. |
| Client (`CLIENT`) | Consultation en lecture seule des formations et sessions client associées. |

Les superusers Django sont traités comme Super Admin. Les contrôles Angular sont complémentaires ; chaque accès aux données est de nouveau contrôlé par DRF et/ou le filtrage de queryset.

## E. Modules fonctionnels

| Module | Niveau | Workflows présents |
|---|---|---|
| Authentification et comptes | Complet | Connexion JWT, refresh/rotation/blacklist, profil, langue, coordonnées, changement et reset de mot de passe, import utilisateurs. |
| Rôles et permissions | Complet | Huit rôles, guards, menus filtrés, permissions objet et périmètres BU. |
| Business Units | Complet | BU, managers, adhésions, membres, besoins, priorités, décisions et historique. |
| Recrutement | Complet | Offres, publication, candidatures, documents, transitions, rejet, entretien, conversion. |
| CV et matching | Fonctionnel avec limites | PDF/DOCX, extraction structurée, score/matching et recommandations ; OCR d'image pure non garanti. |
| Stagiaires/collaborateurs | Complet | Profils, BU/tuteur, dossiers, exigences documentaires, validations, évaluations et vues RH. |
| Formations | Complet | Catalogue, sessions, inscriptions, décisions, présences, historique, certificats et vues client. |
| Projets | Complet | Projets, affectations, livrables, commentaires et documents. |
| Notifications/e-mails | Fonctionnel | Centre privé, préférences, signaux, e-mails et journal de livraison ; SMTP externe requis. |
| Dashboards/KPI/rapports | Fonctionnel | Synthèses par rôle/BU, dashboard RH, exports et synchronisation analytique. |
| Audit | Complet | Audit HTTP/métier, événements sensibles et accès réservé. |
| Assistant | Dépendance externe | Conversations privées, message/stream/health, provider Ollama. |

Il n'existe pas de MFA complet dans le code. Il ne faut donc pas le présenter comme livré.

## F. IA et données

L'analyse de CV est principalement un pipeline déterministe, pas un système d'apprentissage entraîné dans le projet. Les PDF textuels sont lus avec PyMuPDF et les DOCX avec `python-docx`. Le pipeline nettoie le texte, identifie des sections et extrait notamment identité/coordonnées, compétences, langues, formation et expériences. Les résultats structurés sont conservés dans `CVAnalysis`.

Le rapprochement compare les données extraites avec les exigences de l'offre et stocke un `ApplicationMatch`. Des `TrainingRecommendation` peuvent signaler les écarts de compétences. Les scores sont des aides à la décision : ils ne remplacent pas une validation humaine et peuvent être affectés par la mise en page, la langue, les synonymes ou un CV incomplet.

Le code traite les PDF/DOCX et contient des stratégies d'extraction améliorées, mais aucun moteur OCR externe pleinement garanti n'est installé/configuré dans les dépendances finales. Un PDF scanné sans couche texte peut donc produire peu ou pas de données ; l'OCR doit être considéré comme partiel/limité, pas comme une promesse universelle.

L'assistant utilise par défaut `OllamaAssistantProvider`, l'URL et le modèle étant configurables. Il expose santé, message, streaming et historique de conversations. Les timeouts et indisponibilités Ollama sont gérés et testés. Sans serveur et modèle Ollama, le reste de l'application fonctionne mais l'assistant reste indisponible.

Améliorations futures possibles, hors clôture : OCR dédié et évalué, dictionnaires multilingues enrichis, calibration des scores sur un jeu validé, métriques de précision/biais et supervision de l'inférence.

## G. Base de données

Le modèle utilisateur personnalisé est au centre des relations. `AccountSecurityLog` garde les événements de compte. `BusinessUnit`, `BusinessUnitMembership`, `BusinessUnitNeed` et son historique organisent les périmètres.

Le recrutement comprend `CandidateProfile`, `Offer`, `Application`, documents, entretiens, historique de statut, profils stagiaire/employé, exigences et dépôts documentaires, évaluations, audit sensible, analyses CV, matches et recommandations. La formation comprend client, formation, session, inscription, historiques, présence et certificat. Les projets regroupent projet, affectation, livrable, commentaire et document. Notifications, préférences, audit et livraisons e-mail complètent la traçabilité. Les tables analytiques `DimDate`, `DimBusinessUnit`, `FactApplication` et `FactTrainingEnrollment` forment un entrepôt léger.

Les migrations retracent l'ajout progressif des coordonnées utilisateurs, journaux de sécurité, besoins BU, workflows de formation, présence, recommandations, analyse CV structurée et méthodes de dépôt. L'audit final confirme qu'aucune modification de modèle non migrée n'existe. MySQL est la cible officielle et a été requalifié avec la chaîne complète des migrations, la restauration des données PostgreSQL et les tests backend.

## H. API REST

Les grands groupes sont :

- `/api/auth/` : token, refresh, verify, blacklist, profil, langue, coordonnées, mot de passe et reset ;
- `/api/users/`, `/api/import/` : administration et import ;
- `/api/business-units/`, memberships et needs ;
- `/api/offers/`, applications, documents, interviews, interns, documents/exigences/évaluations ;
- `/api/trainings/`, sessions, enrollments, attendance, certificates et espaces client ;
- `/api/projects/`, deliverables, comments et documents ;
- `/api/notifications/`, preferences et audit logs ;
- `/api/reports/` : synthèses, dashboards et exports ;
- `/api/chatbot/` et `/api/assistant/conversations/` ;
- endpoints RH dédiés aux stagiaires et collaborateurs.

DRF applique authentification par défaut, pagination et throttling ; seuls les dépôts publics nécessaires redéfinissent explicitement leurs permissions. Swagger, ReDoc et le schéma OpenAPI sont exposés sous `/api/docs/`, `/api/redoc/` et `/api/schema/`. Le schéma se génère sans erreur ; 15 avertissements de nommage d'enums restent documentés.

## I. Frontend Angular

Le frontend utilise des composants standalone et le lazy loading. `core` contient modèles, services, guards, intercepteur, navigation et i18n ; `features` regroupe les domaines ; `layouts` sépare public, authentification et application ; `shared` contient les composants réutilisables.

Les pages couvrent site public, connexion/reset, dashboards, utilisateurs/import, offres/candidatures/CV, BU et besoins, stagiaires, formations/présences/certificats, projets, notifications, rapports, audit et profil. Les formulaires sont typés et validés côté client avant la validation serveur. L'intercepteur ajoute JWT et sérialise une requête de refresh concurrente. La navigation et les routes sont filtrées par rôle. Les améliorations récentes portent sur les états vides, la responsivité et la cohérence des espaces par rôle.

Le strict TypeScript est inclus dans la compilation Angular. Aucun script de lint distinct n'est configuré dans `package.json`; il n'a donc pas été inventé ni déclaré comme exécuté.

## J. Sécurité finale

- JWT court (15 minutes par défaut), refresh 7 jours, rotation et blacklist ;
- mots de passe Django, validateurs standards et reset limité à 30 minutes ;
- permissions DRF globales et spécialisées, filtrage objet/queryset et séparation RH/Super Admin ;
- guards et navigation Angular comme couche UX supplémentaire ;
- CORS sur liste explicite, CSRF trusted origins et cookies sécurisés en production ;
- redirection HTTPS, HSTS, `nosniff`, politique referrer et proxy SSL en production ;
- limites de taille, extensions/MIME/signatures et validations métier pour les uploads selon le domaine ;
- `.env` ignorés par Git, production exigeant une clé secrète ; aucun fichier `.env` suivi ;
- throttling anonyme, utilisateur, connexion, dépôts publics, comptes sensibles et chatbot ;
- audit général, sécurité de compte, audit sensible recrutement et journal des e-mails.

Limites : pas de MFA ; HTTPS dépend du reverse proxy/hébergeur ; le stockage local de médias doit être rendu persistant et sauvegardé ; une analyse antivirus externe des pièces jointes n'est pas intégrée.

## K. Déploiement

### Local

Python 3.12+, MySQL 8 et Node 22 sont documentés. Le backend utilise un venv et les requirements local ; Angular utilise `npm install`/`npm start` et un proxy vers le port 8001.

### Docker

Compose définit MySQL 8, backend Gunicorn et frontend Nginx. Les volumes persistent la base et les médias. Nginx sert la SPA et relaie API/médias. La configuration Compose a été validée ; l'image complète doit encore être qualifiée sur l'infrastructure cible avant de revendiquer un déploiement effectif.

### cPanel/Passenger

Le script crée les répertoires persistants, synchronise sans secrets/médias, installe les dépendances, vérifie Django, migre, collecte les statiques, publie Angular et redémarre Passenger. Il accepte un Python cPanel configurable et contient une compatibilité MySQL motivée par les contraintes d'hébergement. L'infrastructure cPanel réelle n'était pas disponible : cette voie est configurée mais non validée de bout en bout.

### Render/Vercel

Aucune configuration Render ou Vercel active n'est présente dans l'état final ; aucune mise en ligne sur ces services n'est revendiquée.

### Statut

Localement validé : oui pour checks/tests/build. Configuré pour production : oui, sous réserve des variables et services. Effectivement déployé et supervisé : non démontré par le dépôt ou cet audit.

## L. Principaux problèmes rencontrés et solutions

| Problème | Solution retenue |
|---|---|
| Contrats frontend/backend et statuts divergents | Modèles TypeScript, serializers, enums/migrations de normalisation et tests d'intégration. |
| Confusion de droits RH/administrateur | Helpers de rôles explicites, permissions safe-method pour RH, routes/navigation réalignées et matrice de tests. |
| Périmètres Business Unit | Memberships, manager nullable contrôlé, filtrage de querysets et historique des besoins. |
| Migrations et données seed | Migrations successives, commandes contrôlées, test runner isolé et `makemigrations --check`. |
| CV hétérogènes | Extraction PDF/DOCX, nettoyage/sections, champs structurés et validation humaine obligatoire. |
| PDF scannés/OCR | Dégradation contrôlée et limitation documentée ; pas de promesse d'OCR complet. |
| Refresh JWT concurrent | Intercepteur partagé avec une seule requête de refresh et logout sur échec. |
| E-mails indisponibles | Backend console en local, SMTP configurable en production, journal des livraisons et gestion d'erreurs. |
| Assistant local indisponible/timeout | Provider isolé, health check, timeouts, erreurs explicites et tests simulés. |
| Builds Angular lourds | Limite mémoire Node explicite, lazy loading et build de production en CI. |
| Déploiement cPanel/Python/DB | Passenger, chemins configurables, script fail-fast et configuration MySQL. |
| Persistance Docker | Volumes MySQL/médias, healthcheck DB et ordre de démarrage. |
| Journal de production Docker absent | Création de `/app/logs` dans l'image et droits attribués à l'utilisateur non-root. |
| Variables de sécurité absentes en CI | Ajout d'hosts/origins explicites au job backend. |

## M. Stabilisation finale

### Problèmes constatés et corrections

1. **CI production incomplète** — `production.py` exige `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS`, absents du job. Ajout des valeurs CI explicites, ainsi que CORS.
2. **Journal fichier Docker** — le handler écrivait dans `/app/logs/django.log`, mais le Dockerfile ne créait pas `/app/logs`. Création avant le passage à l'utilisateur non-root.
3. **Exemple d'environnement incomplet** — ajout des limites recrutement/rétention, options SMTP et paramètres assistant/Ollama dans `.env.example`.
4. **Documentation de statut obsolète** — README passé de « phase finale » à un statut de clôture transparent, avec lien vers ce rapport.
5. **Bruit OpenAPI** — 15 avertissements de collisions/noms d'enums, zéro erreur. Aucun override risqué ajouté en phase finale ; avertissements conservés comme dette non bloquante.
6. **Première exécution Angular sous sandbox** — échec d'accès aux chemins parents, sans fichier manquant réel. Rejouée hors sandbox : succès. Il s'agit d'une contrainte de l'outil d'audit, pas d'un défaut du projet.

### Fichiers modifiés lors de cette clôture

- `.github/workflows/ci.yml`
- `backend/Dockerfile`
- `.env.example`
- `README.md`
- `FINAL_PROJECT_REPORT.md`

Huit fichiers frontend contenaient déjà des modifications non commitées au début de l'audit. Ils ont été préservés et ne sont pas attribués à cette clôture.

### Tests et contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `python manage.py check` (venv projet) | Succès, 0 problème. |
| `python manage.py makemigrations --check --dry-run` | Succès, aucune modification détectée. |
| `python -m pip check` | Succès, aucune dépendance cassée. |
| `python manage.py test --noinput` | **279/279 succès** en 18,6 s. |
| `npm run build` | Succès, bundle production généré ; initial 463,15 kB brut. |
| `npm test -- --watch=false --browsers=ChromeHeadless` | **172/172 succès**. |
| TypeScript/Angular strict | Succès via compilation de production et compilation des tests. |
| `manage.py check --deploy --settings=config.settings.production` | Succès ; uniquement les 15 avertissements OpenAPI décrits. |
| `manage.py spectacular --validate` | 0 erreur, 15 avertissements de nommage d'enums. |
| `docker compose config --quiet` | Succès ; avertissement local d'accès au fichier global Docker, sans erreur Compose. |
| Recherche TODO/FIXME/debug/mock | Aucun TODO/FIXME/hack/debugger/console.log applicatif dangereux ; seuls deux `print` historiques dans une migration de seed. |
| Recherche secrets/fichiers suivis | Aucun `.env`, SQLite, média, log ou clé privée suivi. Les seules valeurs trouvées sont des exemples/build-only. |
| Lint Angular | Non exécuté : aucun script/configuration lint n'est présent. |
| MySQL réel local | MySQL 8.0.46 validé avec 75 migrations, restauration de données et 294 tests backend. |
| Build complet des images Docker | Non exécuté dans cet environnement. |
| SMTP/Ollama/cPanel réels | Non disponibles ; chemins d'échec ou mocks couverts par tests. |

### Avertissements restants

Les tests affichent volontairement des logs d'échec simulé pour import, e-mail, login et Ollama. Angular affiche aussi la clé i18n inexistante testée. Ces messages accompagnent des assertions qui passent. Les 15 avertissements drf-spectacular concernent uniquement la stabilité des noms d'enums du schéma généré.

## N. État final par module

| Module | Statut | Tests | Notes |
|---|---|---|---|
| Comptes/JWT/reset | Stable | Backend + frontend | SMTP requis pour reset réel. |
| Rôles/permissions | Stable | Matrice API/guards | Backend reste source de vérité. |
| Business Units | Stable | Backend + composants | Seeds officiels présents. |
| Recrutement/offres | Stable | Backend + composants | Workflow et transitions couverts. |
| Candidatures/documents | Stable | API + UI | Stockage média persistant requis. |
| CV extraction/matching | Fonctionnel | Tests intelligence/workflow | OCR Tesseract optionnel, score explicable, synthèse et classement ; validation humaine. |
| Stagiaires/collaborateurs | Stable | Backend + UI | Vues RH volontairement read-only. |
| Formations/sessions | Stable | Backend + UI | E-mail/rappels dépendent du SMTP/ordonnanceur. |
| Présence/certificats | Stable | Backend + UI | PDF généré côté serveur. |
| Projets/livrables | Stable | Backend + services UI | Accès limité aux participants. |
| Notifications/audit | Stable | Backend + UI | Livraison e-mail externe configurable. |
| Dashboards/KPI/rapports | Fonctionnel | Backend + UI | Données réelles nécessaires pour qualification volumétrique. |
| Entrepôt analytique | Fonctionnel | Tests sync | Synchronisation déclenchée par commande. |
| Assistant Ollama | Dépendance externe | Tests mocks/timeouts | Serveur/modèle non inclus. |
| OpenAPI/Swagger | Fonctionnel | Génération validée | 15 avertissements enum. |
| Angular production | Stable | Build + 172 tests | Aucun lint séparé configuré. |
| MySQL | Validé localement | Migrations/CI configurées | Instance de production à provisionner. |
| Docker | Besoin validation cible | Compose validé | Images non construites durant cet audit. |
| cPanel/Passenger | Besoin validation cible | Revue statique | Dépend des chemins, Python et droits hébergeur. |

## O. Limites restantes

- Ollama, son modèle et ses ressources système ne sont pas livrés avec l'application.
- Le SMTP réel, les DNS expéditeur et la délivrabilité ne sont pas validés.
- Aucun déploiement réel, test de charge, monitoring ou alerte production n'a été exécuté.
- MySQL cible, sauvegarde et restauration doivent être validés sur l'infrastructure finale.
- Le stockage média est local ; il exige volume persistant, sauvegarde et éventuellement stockage objet en production.
- Pas d'antivirus externe pour les fichiers ; les validations portent sur taille/type/contenu attendu.
- OCR des scans image-only disponible en fallback si Tesseract et ses langues sont installés ; indisponibilité signalée sans plantage.
- Les scores CV ne sont ni un modèle ML calibré ni une décision automatique.
- Pas de MFA.
- MySQL/cPanel est la configuration cible ; l'hébergement cPanel réel reste à qualifier.
- Les migrations seed affichent deux messages console historiques, sans impact d'exécution.
- 15 avertissements de noms d'enums OpenAPI restent à traiter uniquement si un client généré exige des noms stables.
- Les huit modifications frontend préexistantes au worktree doivent être revues/commitées par leur auteur.

## P. Conclusion et verdict

**Démonstration : stable.** Les workflows centraux, permissions, tests et build sont validés.

**Livraison académique : stable.** Le projet est reproductible, documenté, migrable et transparent sur ses limites.

**Production : prête avec travaux d'exploitation, pas encore certifiée.** Le code et la configuration offrent une base sérieuse, mais « production-ready » implique une qualification sur la cible : secrets forts, domaine/HTTPS, MySQL persistant, SMTP, médias/sauvegardes, Ollama éventuel, construction des images, migrations, smoke tests, supervision et plan de restauration.

### Verdict final

**READY WITH LIMITATIONS** — application clôturée et stabilisée pour démonstration/livraison académique ; mise en production possible après configuration et validation opérationnelle de l'environnement cible.
