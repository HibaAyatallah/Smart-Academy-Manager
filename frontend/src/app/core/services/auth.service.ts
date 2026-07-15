import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { catchError, finalize, map, shareReplay, switchMap, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  AuthTokens,
  LoginRequest,
  RefreshTokenResponse,
  UserProfile,
} from '../models/auth.models';
import { ROLE_DASHBOARD_PATHS } from '../utils/role-dashboard';
import { TokenStorageService } from './token-storage.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly tokenStorage = inject(TokenStorageService);
  private readonly apiBaseUrl = environment.apiBaseUrl;
  private readonly currentUserSubject = new BehaviorSubject<UserProfile | null>(null);
  private profileRequest$: Observable<UserProfile> | null = null;
  private profileRequestVersion = 0;

  readonly currentUser$ = this.currentUserSubject.asObservable();

  get currentUserSnapshot(): UserProfile | null {
    return this.currentUserSubject.value;
  }

  get hasAccessToken(): boolean {
    return Boolean(this.tokenStorage.accessToken);
  }

  login(credentials: LoginRequest): Observable<UserProfile> {
    return this.http
      .post<AuthTokens>(`${this.apiBaseUrl}auth/token/`, credentials)
      .pipe(
        map((tokens) => {
          if (!tokens.access || !tokens.refresh) {
            throw new Error('JWT response must contain access and refresh tokens.');
          }
          return tokens;
        }),
        tap((tokens) => {
          this.tokenStorage.saveTokens(tokens);
          this.clearProfileState();
        }),
        switchMap(() => this.loadProfile()),
        catchError((error: unknown) => {
          console.error('[Auth] Échec de connexion.');
          return throwError(() => error);
        }),
      );
  }

  loadProfile(): Observable<UserProfile> {
    return this.requestProfile();
  }

  /** Restores a persisted session before the router starts its first navigation. */
  restoreSession(): Observable<UserProfile | null> {
    const currentUser = this.currentUserSubject.value;
    if (currentUser) {
      return of(currentUser);
    }
    if (!this.hasAccessToken) {
      return of(null);
    }

    return this.requestProfile().pipe(
      catchError(() => {
        this.tokenStorage.clear();
        this.clearProfileState();
        return of(null);
      }),
    );
  }

  ensureProfile(): Observable<UserProfile> {
    const currentUser = this.currentUserSubject.value;
    if (currentUser) {
      return of(currentUser);
    }
    if (!this.hasAccessToken) {
      return throwError(() => new Error('No access token available.'));
    }
    return this.requestProfile();
  }

  refreshAccessToken(): Observable<string> {
    const refresh = this.tokenStorage.refreshToken;
    if (!refresh) {
      return throwError(() => new Error('No refresh token available.'));
    }

    return this.http
      .post<RefreshTokenResponse>(`${this.apiBaseUrl}auth/token/refresh/`, { refresh })
      .pipe(
        tap((response) => this.tokenStorage.saveRefreshResponse(response)),
        map((response) => response.access),
      );
  }

  changePassword(payload: { current_password: string; new_password: string }): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${this.apiBaseUrl}auth/change-password/`, payload);
  }

  logout(redirect = true): void {
    this.tokenStorage.clear();
    this.clearProfileState();
    if (redirect) {
      void this.router.navigateByUrl('/login');
    }
  }

  getDashboardUrlForRole(role: UserProfile['role']): string {
    return ROLE_DASHBOARD_PATHS[role];
  }

  private requestProfile(): Observable<UserProfile> {
    if (this.profileRequest$) {
      return this.profileRequest$;
    }

    const requestVersion = ++this.profileRequestVersion;
    this.profileRequest$ = this.http.get<UserProfile>(`${this.apiBaseUrl}auth/me/`).pipe(
      tap((profile) => {
        // Guard: do not overwrite a state that was intentionally cleared
        // (e.g. a logout/login triggered while this request was in-flight).
        if (requestVersion === this.profileRequestVersion) {
          this.currentUserSubject.next(profile);
        }
      }),
      catchError((error: unknown) => {
        console.error('[Auth] Échec du chargement du profil.');
        return throwError(() => error);
      }),
      finalize(() => {
        // Always release the shared reference so the next caller gets a
        // fresh Observable. The version guard in tap() already prevents
        // stale data from reaching currentUserSubject.
        this.profileRequest$ = null;
      }),
      shareReplay(1),
    );
    return this.profileRequest$;
  }

  private clearProfileState(): void {
    // Increment version so any in-flight tap() call is ignored.
    this.profileRequestVersion += 1;
    this.profileRequest$ = null;
    this.currentUserSubject.next(null);
  }
}
