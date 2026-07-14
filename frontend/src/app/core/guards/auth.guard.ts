import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.hasAccessToken) {
    return router.createUrlTree(['/login'], {
      queryParams: {
        returnUrl: state.url,
      },
    });
  }

  if (authService.currentUserSnapshot) {
    return true;
  }

  return authService.ensureProfile().pipe(
    map(() => true),
    catchError(() => {
      console.error('[Auth] Profil de session invalide.');
      authService.logout(false);
      return of(
        router.createUrlTree(['/login'], {
          queryParams: {
            returnUrl: state.url,
          },
        }),
      );
    }),
  );
};
