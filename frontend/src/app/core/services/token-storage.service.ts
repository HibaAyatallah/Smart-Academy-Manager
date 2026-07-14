import { Injectable } from '@angular/core';

import { AuthTokens, RefreshTokenResponse } from '../models/auth.models';

const ACCESS_TOKEN_KEY = 'smart_academy_access_token';
const REFRESH_TOKEN_KEY = 'smart_academy_refresh_token';

@Injectable({
  providedIn: 'root',
})
export class TokenStorageService {
  get accessToken(): string | null {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  get refreshToken(): string | null {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  saveTokens(tokens: AuthTokens): void {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
  }

  saveRefreshResponse(response: RefreshTokenResponse): void {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, response.access);
    if (response.refresh) {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh);
    }
  }

  clear(): void {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}
