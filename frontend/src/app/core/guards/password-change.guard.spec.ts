import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { of } from 'rxjs';

import { UserProfile } from '../models/auth.models';
import { AuthService } from '../services/auth.service';
import { passwordChangeGuard } from './password-change.guard';

const temporaryUser: UserProfile = {
  id: 1,
  email: 'temporary@test.com',
  first_name: 'Temporary',
  last_name: 'User',
  full_name: 'Temporary User',
  phone_number: '',
  role: 'EMPLOYEE',
  must_change_password: true,
};

describe('passwordChangeGuard', () => {
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue(new UrlTree());
    TestBed.configureTestingModule({
      providers: [{ provide: Router, useValue: router }],
    });
  });

  function run(user: UserProfile | null, url: string) {
    const auth = {
      currentUserSnapshot: user,
      ensureProfile: jasmine.createSpy().and.returnValue(of(user)),
      logout: jasmine.createSpy(),
    };
    TestBed.overrideProvider(AuthService, { useValue: auth });
    return TestBed.runInInjectionContext(() => passwordChangeGuard(
      {} as ActivatedRouteSnapshot,
      { url } as RouterStateSnapshot,
    ));
  }

  it('redirects a temporary-password account away from business routes', () => {
    expect(run(temporaryUser, '/dashboard') instanceof UrlTree).toBeTrue();
    expect(router.createUrlTree).toHaveBeenCalledOnceWith(['/profile']);
  });

  it('allows the password-change profile route', () => {
    expect(run(temporaryUser, '/profile')).toBeTrue();
  });

  it('allows normal navigation after the profile flag is cleared', () => {
    expect(run({ ...temporaryUser, must_change_password: false }, '/dashboard')).toBeTrue();
  });
});
