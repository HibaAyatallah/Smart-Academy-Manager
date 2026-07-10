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

