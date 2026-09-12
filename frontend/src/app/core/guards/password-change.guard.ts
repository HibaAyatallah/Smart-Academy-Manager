import { inject } from '@angular/core';
import { CanActivateChildFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { UserProfile } from '../models/auth.models';
import { AuthService } from '../services/auth.service';

const checkAccess = (user: UserProfile, targetUrl: string, router: Router) =>
  user.must_change_password && !targetUrl.startsWith('/profile')
    ? router.createUrlTree(['/profile'])
    : true;

export const passwordChangeGuard: CanActivateChildFn = (_route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const snapshot = authService.currentUserSnapshot;

  if (snapshot) {
    return checkAccess(snapshot, state.url, router);
  }

  return authService.ensureProfile().pipe(
    map((user) => checkAccess(user, state.url, router)),
    catchError(() => {
      authService.logout(false);
      return of(router.createUrlTree(['/connexion']));
    }),
  );
};
