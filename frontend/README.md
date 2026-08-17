# Frontend — Smart Academy Manager

Le frontend est l’interface utilisateur de Smart Academy Manager. Il est développé avec **Angular**, **TypeScript** et **Angular Material**.

## Organisation

- `src/app/core` : services HTTP, modèles, guards, interceptors, navigation et internationalisation ;
- `src/app/features` : écrans métier par domaine ;
- `src/app/layouts` : layouts public, authentifié et connexion ;
- `src/app/shared` : composants et directives réutilisables ;
- `src/environments` : configuration des environnements.

L’application communique exclusivement avec l’API Django. L’intercepteur d’authentification transmet les jetons JWT, tandis que les guards contrôlent l’accès aux routes selon la connexion et le rôle. Les permissions Django restent la source de vérité côté serveur.

## Installation

```powershell
npm install
```

## Développement

```powershell
npm start
```

L’application démarre sur `http://localhost:4200`. Le proxy de développement redirige les appels API vers Django.

## Build de production

```powershell
npm run build
```

Les fichiers générés sont placés dans le répertoire `dist/` défini par Angular.

## Tests

```powershell
npm test -- --watch=false --browsers=ChromeHeadless
```
