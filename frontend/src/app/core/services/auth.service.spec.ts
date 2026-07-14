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
};

describe('AuthService', () => {
  let service: AuthService;
  let httpController: HttpTestingController;

  beforeEach(() => {
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
          useValue: {
            accessToken: 'access-token',
            refreshToken: 'refresh-token',
            saveTokens: jasmine.createSpy(),
            saveRefreshResponse: jasmine.createSpy(),
            clear: jasmine.createSpy(),
          },
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
});
