# API foundation

## Authentification

Endpoints JWT :

- `POST /api/auth/token/` : obtenir un access token et un refresh token ;
- `POST /api/auth/token/refresh/` : renouveler l'access token ;
- `POST /api/auth/token/verify/` : verifier un token ;
- `GET /api/auth/me/` : recuperer le profil connecte ;
- `PATCH /api/auth/me/` : mettre a jour les champs autorises de son profil.

## Utilisateurs

Endpoints reserves aux roles internes autorises :

- `GET /api/users/`
- `POST /api/users/`
- `GET /api/users/{id}/`
- `PATCH /api/users/{id}/`
- `DELETE /api/users/{id}/`

## Roles disponibles

- `SUPER_ADMIN`
- `HR`
- `BU_MANAGER`
- `TRAINER_TUTOR`
- `EMPLOYEE`
- `INTERN`
- `CANDIDATE`
- `CLIENT`

## Candidatures

Endpoints principaux :

- `POST /api/applications/public-submit/` : depot public d'une candidature et creation du compte candidat ;
- `GET /api/applications/mine/` : candidatures du candidat connecte ;
- `GET /api/applications/` : liste filtree pour RH et super administrateur ;
- `GET /api/applications/{id}/` : detail d'une candidature autorisee ;
- `POST /api/applications/{id}/documents/` : ajout d'un document ;
- `GET /api/applications/{id}/history/` : historique des statuts ;
- `POST /api/applications/{id}/mark-under-review/` ;
- `POST /api/applications/{id}/preselect/` ;
- `POST /api/applications/{id}/schedule-interview/` ;
- `POST /api/applications/{id}/complete-interview/` ;
- `POST /api/applications/{id}/accept/` ;
- `POST /api/applications/{id}/reject/` ;
- `POST /api/applications/{id}/cancel/`.

Filtres RH :

- `GET /api/applications/?application_type=PFA_INTERNSHIP`
- `GET /api/applications/?status=SUBMITTED`
- `GET /api/applications/?search=nom-ou-email`

Types de candidature :

- `PFA_INTERNSHIP`
- `PFE_INTERNSHIP`
- `HIRING`

Champs requis pour `POST /api/applications/public-submit/` :

- `first_name`
- `last_name`
- `email`
- `password`
- `phone_number`
- `application_type`
- `current_school`
- `study_level`
- `study_field`
- `cv`
- `cover_letter`
- `personal_photo`

Champ conditionnel :

- `study_level_other` : requis uniquement lorsque `study_level` vaut `OTHER`.

Niveaux d'etudes :

- `FIRST_YEAR`
- `SECOND_YEAR`
- `THIRD_YEAR`
- `FOURTH_YEAR`
- `FIFTH_YEAR`
- `BACHELOR`
- `MASTER`
- `ENGINEERING`
- `DOCTORATE`
- `OTHER`

Documents requis :

- `cv` : PDF, DOC ou DOCX, 5 Mo maximum ;
- `cover_letter` : PDF, DOC ou DOCX, 5 Mo maximum ;
- `personal_photo` : JPG, JPEG ou PNG, 3 Mo maximum.

Les tailles maximales sont configurees par `RECRUITMENT_MAX_UPLOAD_SIZE_MB` pour les documents, avec `5` Mo par defaut, et `RECRUITMENT_PHOTO_MAX_UPLOAD_SIZE_MB` pour la photo, avec `3` Mo par defaut.

Statuts :

- `SUBMITTED`
- `UNDER_REVIEW`
- `PRESELECTED`
- `INTERVIEW_SCHEDULED`
- `INTERVIEW_COMPLETED`
- `ACCEPTED`
- `REJECTED`
- `CANCELLED`

Regles de securite :

- le candidat voit uniquement ses propres candidatures ;
- le RH peut consulter et traiter les candidatures ;
- le super administrateur peut tout administrer ;
- les autres roles n'ont pas acces au module.

Commande de conservation des donnees :

```powershell
python manage.py anonymize_expired_applications
```
