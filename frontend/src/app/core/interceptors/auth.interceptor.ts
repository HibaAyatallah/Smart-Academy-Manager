import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, shareReplay, switchMap, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { TokenStorageService } from '../services/token-storage.service';

let refreshRequest$: Observable<string> | null = null;

const isAuthEndpoint = (url: string): boolean => url.includes('/auth/token/');

const addAuthorizationHeader = (
  request: HttpRequest<unknown>,
  token: string,
): HttpRequest<unknown> =>
  request.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`,
    },
  });

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const tokenStorage = inject(TokenStorageService);
  const authService = inject(AuthService);
  const router = inject(Router);
  const accessToken = tokenStorage.accessToken;
  const shouldAttachToken = Boolean(accessToken) && !isAuthEndpoint(request.url);
  const requestWithToken =
    shouldAttachToken && accessToken
      ? addAuthorizationHeader(request, accessToken)
      : request;

  return next(requestWithToken).pipe(
    catchError((error: HttpErrorResponse) => {
      const canRefresh =
        error.status === 401 && !isAuthEndpoint(request.url) && Boolean(tokenStorage.refreshToken);

      if (!canRefresh) {
        console.error(`[Auth] Requête HTTP échouée (statut ${error.status}).`);
        return throwError(() => error);
      }

      refreshRequest$ ??= authService.refreshAccessToken().pipe(
        finalize(() => {
          refreshRequest$ = null;
        }),
        shareReplay(1),
      );

      return refreshRequest$.pipe(
        switchMap((newAccessToken) => next(addAuthorizationHeader(request, newAccessToken))),
        catchError((refreshError: unknown) => {
          console.error('[Auth] Échec du renouvellement de session.');
          authService.logout(false);
          void router.navigateByUrl('/login');
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
