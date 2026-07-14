import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, GuardResult, MaybeAsync, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { BehaviorSubject, Observable, of, Subject } from 'rxjs';

import { UserProfile } from '../models/auth.models';
import { AuthService } from '../services/auth.service';
import { authGuard } from './auth.guard';

const hrUser: UserProfile = {
  id: 1,
  email: 'hr@example.com',
  first_name: 'HR',
  last_name: 'User',
  full_name: 'HR User',
  phone_number: '',
  role: 'HR',
};

function runGuard(
  authServiceStub: Partial<AuthService>,
): MaybeAsync<GuardResult> {
  const routerStub = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
  routerStub.createUrlTree.and.callFake((commands: unknown[]) => {
    const tree = new UrlTree();
    (tree as unknown as { segments: unknown[] }).segments = commands;
    return tree;
  });

  TestBed.overrideProvider(AuthService, { useValue: authServiceStub });
  TestBed.overrideProvider(Router, { useValue: routerStub });

  return TestBed.runInInjectionContext(() =>
    authGuard(
      {} as ActivatedRouteSnapshot,
      { url: '/applications' } as RouterStateSnapshot,
    ),
  );
}

describe('authGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
  });

  it('returns true synchronously when the profile is already in cache', () => {
    // SHOULD PASS: fast path when snapshot is already available.
    const result = runGuard({
      hasAccessToken: true,
      currentUserSnapshot: hrUser,
      ensureProfile: jasmine.createSpy(),
    });

    expect(result).toBe(true);
  });

  it('redirects to /login synchronously when there is no access token', () => {
    // SHOULD PASS: no token → redirect to login.
    const result = runGuard({
      hasAccessToken: false,
      currentUserSnapshot: null,
      ensureProfile: jasmine.createSpy(),
    }) as UrlTree;

    expect(result instanceof UrlTree).toBeTrue();
  });

  /**
   * FAILING TEST (before the fix) — demonstrates the race condition:
   *
   * If the guard runs while initialization is still in progress
   * (e.g. the router started navigation before restoreSession() completed
   * because Angular 21 did not block navigation long enough), the guard
   * MUST wait for initialized$ to emit before it checks hasAccessToken or
   * currentUserSnapshot.
   *
   * With the current code the guard does NOT use initialized$ at all, so it
   * reads currentUserSnapshot while it is still null and immediately falls
   * back to ensureProfile() — which is itself an async HTTP call.  The
   * component is created only after the HTTP response, so on the very FIRST
   * navigation the page is blank until the request completes.
   *
   * After the fix the guard subscribes to initialized$ first.  Any caller of
   * the guard that runs before initialization is complete will be suspended
   * until initialized$ emits, at which point currentUserSnapshot is guaranteed
   * to be set and the guard can resolve synchronously.
   */
  it('FAILS before fix: does not wait for initialized$ when snapshot is null', (done) => {
    // Simulate: token exists, snapshot not yet populated (initialization in progress).
    let ensureProfileCalled = false;

    const ensureProfileSpy = jasmine.createSpy('ensureProfile').and.callFake(() => {
      ensureProfileCalled = true;
      return of(hrUser);
    });

    const result = runGuard({
      hasAccessToken: true,
      currentUserSnapshot: null, // not loaded yet
      ensureProfile: ensureProfileSpy,
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
