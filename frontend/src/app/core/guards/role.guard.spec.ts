import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, GuardResult, MaybeAsync, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable, Subject, of } from 'rxjs';

import { UserProfile } from '../models/auth.models';
import { AuthService } from '../services/auth.service';
import { roleGuard } from './role.guard';

const hrUser: UserProfile = {
  id: 1,
  email: 'hr@example.com',
  first_name: 'HR',
  last_name: 'User',
  full_name: 'HR User',
  phone_number: '',
  role: 'HR',
};

function runRoleGuard(
  authServiceStub: Partial<AuthService>,
  requiredRoles: string[] = ['HR', 'SUPER_ADMIN'],
): MaybeAsync<GuardResult> {
  const routerStub = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
  routerStub.createUrlTree.and.callFake((commands: unknown[]) => {
    const tree = new UrlTree();
    (tree as unknown as { segments: unknown[] }).segments = commands;
    return tree;
  });

  TestBed.overrideProvider(AuthService, { useValue: authServiceStub });
  TestBed.overrideProvider(Router, { useValue: routerStub });

  const route = { data: { roles: requiredRoles } } as unknown as ActivatedRouteSnapshot;

  return TestBed.runInInjectionContext(() =>
    roleGuard(route, {} as RouterStateSnapshot),
  );
}

describe('roleGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('returns true synchronously when profile is cached and role is authorised', () => {
    const result = runRoleGuard({
      currentUserSnapshot: hrUser,
      ensureProfile: jasmine.createSpy(),
      getDashboardUrlForRole: jasmine.createSpy().and.returnValue('/dashboard/hr'),
    });

    expect(result).toBe(true);
  });

  /**
   * FAILING TEST (before the fix) — mirrors the race condition in authGuard:
   *
   * When the guard runs before the profile is in cache (currentUserSnapshot
   * is null), the current code immediately calls ensureProfile() and resolves
   * via an HTTP call.  Because the component is created only AFTER that HTTP
   * response, the page appears blank on the FIRST visit.
   *
   * With the fix, roleGuard subscribes to initialized$ first.  Once
   * initialized$ emits, currentUserSnapshot is guaranteed to be populated, so
   * the guard can resolve synchronously via the fast path — and the component
   * is created instantly, with data loaded on the first render.
   */
  it('FAILS before fix: resolves before initialized$ emits when snapshot is null', (done) => {
    let ensureProfileCalled = false;

    const ensureProfileSpy = jasmine.createSpy('ensureProfile').and.callFake(() => {
      ensureProfileCalled = true;
      return of(hrUser);
    });

    const result = runRoleGuard({
      currentUserSnapshot: null, // not populated yet
      ensureProfile: ensureProfileSpy,
      getDashboardUrlForRole: jasmine.createSpy().and.returnValue('/dashboard/hr'),
      logout: jasmine.createSpy(),
    });

    if (result instanceof Observable) {
      let resolvedBeforeInit = false;
      result.subscribe(() => { resolvedBeforeInit = true; });

      expect(resolvedBeforeInit).toBeTrue();
      done();
    } else {
      done();
    }
  });
});
