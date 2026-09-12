import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { UserProfile } from '../models/auth.models';
import { TokenStorageService } from './token-storage.service';
import { AuthService } from './auth.service';

const profile: UserProfile = {
  id: 1,
  email: 'candidate@example.com',
  first_name: 'Jane',
  last_name: 'Candidate',
  full_name: 'Jane Candidate',
  phone_number: '+212600000000',
  role: 'CANDIDATE',
  preferred_language: 'fr',
};

describe('AuthService', () => {
  let service: AuthService;
  let httpController: HttpTestingController;
  let tokenStorage: jasmine.SpyObj<TokenStorageService> & {
    accessToken: string | null;
    refreshToken: string | null;
  };

  beforeEach(() => {
    tokenStorage = Object.assign(
      jasmine.createSpyObj<TokenStorageService>('TokenStorageService', [
        'saveTokens',
        'saveRefreshResponse',
        'clear',
      ]),
      { accessToken: 'access-token', refreshToken: 'refresh-token' },
    );
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Router,
          useValue: { navigateByUrl: jasmine.createSpy().and.resolveTo(true) },
        },
        {
          provide: TokenStorageService,
          useValue: tokenStorage,
        },
      ],
    });
    service = TestBed.inject(AuthService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpController.verify());

  it('shares the profile restoration request across simultaneous consumers', () => {
    const profiles: UserProfile[] = [];

    service.ensureProfile().subscribe((user) => profiles.push(user));
    service.ensureProfile().subscribe((user) => profiles.push(user));

    const request = httpController.expectOne('/api/auth/me/');
    request.flush(profile);

    expect(profiles).toEqual([profile, profile]);
    expect(service.currentUserSnapshot).toEqual(profile);
  });

  it('shares the startup restoration request with a guard profile request', () => {
    const restoredProfiles: Array<UserProfile | null> = [];
    const guardProfiles: UserProfile[] = [];

    service.restoreSession().subscribe((user) => restoredProfiles.push(user));
    service.ensureProfile().subscribe((user) => guardProfiles.push(user));

    const request = httpController.expectOne('/api/auth/me/');
    request.flush(profile);

    expect(restoredProfiles).toEqual([profile]);
    expect(guardProfiles).toEqual([profile]);
  });

  it('uses the restored profile without making another API request', () => {
    service.ensureProfile().subscribe();
    httpController.expectOne('/api/auth/me/').flush(profile);

    const restoredProfiles: UserProfile[] = [];
    service.ensureProfile().subscribe((user) => {
      restoredProfiles.push(user);
    });

    httpController.expectNone('/api/auth/me/');
    expect(restoredProfiles).toEqual([profile]);
  });

  it('persists the language and updates the cached profile after confirmation', () => {
    service.ensureProfile().subscribe();
    httpController.expectOne('/api/auth/me/').flush(profile);
    service.updateLanguage('en').subscribe();
    const request = httpController.expectOne('/api/auth/language/');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({preferred_language: 'en'});
    request.flush({preferred_language: 'en'});
    expect(service.currentUserSnapshot?.preferred_language).toBe('en');
  });

  it('blacklists the refresh token and always clears the local session on logout', () => {
    service.ensureProfile().subscribe();
    httpController.expectOne('/api/auth/me/').flush(profile);

    service.logout();

    expect(tokenStorage.clear).toHaveBeenCalled();
    expect(service.currentUserSnapshot).toBeNull();
    const request = httpController.expectOne('/api/auth/token/blacklist/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ refresh: 'refresh-token' });
    request.flush({}, { status: 503, statusText: 'Unavailable' });
    expect(tokenStorage.clear).toHaveBeenCalledTimes(1);
  });

  it('stores rotated tokens and reloads the profile after a password change', () => {
    const profiles: UserProfile[] = [];
    service.changePassword({
      current_password: 'TemporaryPass123!',
      new_password: 'PermanentPass456!',
      confirmation: 'PermanentPass456!',
    }).subscribe((user) => profiles.push(user));

    const change = httpController.expectOne('/api/auth/change-password/');
    change.flush({ detail: 'OK', access: 'new-access', refresh: 'new-refresh' });
    expect(tokenStorage.saveTokens).toHaveBeenCalledWith({
      access: 'new-access', refresh: 'new-refresh',
    });
    httpController.expectOne('/api/auth/me/').flush({
      ...profile,
      must_change_password: false,
    });
    expect(profiles[0].must_change_password).toBeFalse();
  });
});
