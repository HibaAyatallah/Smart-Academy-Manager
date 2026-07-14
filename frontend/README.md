# Smart Academy Manager Frontend

Frontend Angular 21 pour Smart Academy Manager.

## Fondation incluse

- Angular Router ;
- Angular Material ;
- SCSS ;
- formulaires reactifs ;
- appel JWT vers Django REST Framework ;
- stockage de l'access token et du refresh token ;
- interceptor HTTP avec renouvellement du token ;
- recuperation du profil connecte ;
- guard d'authentification ;
- guard par role ;
- layout responsive avec sidebar et navbar ;
- dashboards initiaux par role ;
- depot public de candidature ;
- espace candidat ;
- liste et detail RH des candidatures ;
- actions RH de preselection, entretien, acceptation et refus.

## API locale

L'adresse de l'API Django est configuree dans :

```text
src/environments/environment.ts
```

Valeur actuelle :

```text
http://127.0.0.1:8000/api/
```

## Installation

Dans PowerShell :

```powershell
cd C:\Users\hibaa\OneDrive\Desktop\Smart_Academy_Manager\frontend
npm.cmd install
npm.cmd start
```

Verification :

- application Angular : http://127.0.0.1:4200/
- formulaire public : http://127.0.0.1:4200/apply
- backend Django lance : http://127.0.0.1:8000/api/docs/

La build de production utilise le chemin relatif `/api/`. L'hebergeur devra
router ce chemin vers le backend Django HTTPS; aucun domaine de production
n'est suppose dans le code source.

## Build

```powershell
npm.cmd run build
```
