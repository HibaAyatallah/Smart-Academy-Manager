import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { UserRole } from '../models/auth.models';
import { AuthService } from '../services/auth.service';

const canAccessRole = (
  role: UserRole,
  requiredRoles: UserRole[] | undefined,
): boolean => !requiredRoles?.length || requiredRoles.includes(role);

export const roleGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const requiredRoles = route.data['roles'] as UserRole[] | undefined;

  // Fast-path: if the profile is already in cache (restored by the app
  // initializer or a previous guard), resolve synchronously without
  // creating an Observable subscription.
  const snapshot = authService.currentUserSnapshot;
  if (snapshot) {
    if (canAccessRole(snapshot.role, requiredRoles)) {
      return true;
    }
    return router.createUrlTree([authService.getDashboardUrlForRole(snapshot.role)]);
  }

  return authService.ensureProfile().pipe(
    map((user) => {
      if (canAccessRole(user.role, requiredRoles)) {
        return true;
      }
      const dashboardUrl = authService.getDashboardUrlForRole(user.role);
      return router.createUrlTree([dashboardUrl]);
    }),
    catchError(() => {
      console.error('[Auth] Profil de session invalide.');
      authService.logout(false);
      return of(router.createUrlTree(['/login']));
    }),
  );
};
