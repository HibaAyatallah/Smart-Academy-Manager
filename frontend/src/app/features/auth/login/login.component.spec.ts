import { HttpErrorResponse } from '@angular/common/http';
import { convertToParamMap } from '@angular/router';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { NEVER, of, throwError } from 'rxjs';

import { UserProfile, UserRole } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';
import { ROLE_DASHBOARD_PATHS } from '../../../core/utils/role-dashboard';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', [
      'login',
      'getDashboardUrlForRole',
    ]);
    authService.getDashboardUrlForRole.and.callFake(
      (role) => ROLE_DASHBOARD_PATHS[role],
    );
    router = jasmine.createSpyObj<Router>('Router', ['navigateByUrl']);
    router.navigateByUrl.and.resolveTo(true);

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function fillValidForm(): void {
    component.loginForm.setValue({
      email: 'hr@example.com',
      password: 'StrongPass123!',
    });
  }

  function validProfile(role: UserRole = 'HR'): UserProfile {
    return {
      id: 1,
      email: 'hr@example.com',
      first_name: 'Hiba',
      last_name: 'RH',
      full_name: 'Hiba RH',
      phone_number: '',
      role,
    };
  }

  it('does not start a login request on initialization or with empty fields', () => {
    expect(component.isSubmitting).toBeFalse();
    expect(authService.login).not.toHaveBeenCalled();

    component.onSubmit();

    expect(component.isSubmitting).toBeFalse();
    expect(component.loginForm.touched).toBeTrue();
    expect(authService.login).not.toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('prevents a second submission while a login request is pending', () => {
    fillValidForm();
    authService.login.and.returnValue(NEVER);

    component.onSubmit();
    component.onSubmit();

    expect(component.isSubmitting).toBeTrue();
    expect(authService.login).toHaveBeenCalledTimes(1);
  });

  it('stops loading, shows the 401 error and does not redirect', () => {
    fillValidForm();
    authService.login.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 401 })),
    );

    component.onSubmit();
    fixture.detectChanges();

    expect(component.isSubmitting).toBeFalse();
    expect(component.errorMessage).toBe('Email ou mot de passe incorrect.');
    expect(fixture.nativeElement.querySelector('.alert-error')?.textContent).toContain(
      'Email ou mot de passe incorrect.',
    );
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('stops loading and shows a visible error when the backend does not respond', fakeAsync(() => {
    fillValidForm();
    authService.login.and.returnValue(NEVER);

    component.onSubmit();
    expect(component.isSubmitting).toBeTrue();

    tick(10_001);
    fixture.detectChanges();

    expect(component.isSubmitting).toBeFalse();
    expect(component.errorMessage).toContain('backend ne répond pas');
    expect(fixture.nativeElement.querySelector('.alert-error')?.textContent).toContain(
      'backend ne répond pas',
    );
  }));

  it('submits by clicking the submit button and redirects after a successful login', fakeAsync(() => {
    fillValidForm();
    authService.login.and.returnValue(of(validProfile()));
    fixture.detectChanges();

    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'button[type="submit"]',
    );
    submitButton.click();
    tick();

    expect(component.isSubmitting).toBeFalse();
    expect(authService.login).toHaveBeenCalledOnceWith({
      email: 'hr@example.com',
      password: 'StrongPass123!',
    });
    expect(authService.getDashboardUrlForRole).toHaveBeenCalledOnceWith('HR');
    expect(router.navigateByUrl).toHaveBeenCalledOnceWith('/dashboard/hr');
  }));

  it('submits when Enter is pressed in the password field', fakeAsync(() => {
    fillValidForm();
    authService.login.and.returnValue(of(validProfile()));
    fixture.detectChanges();

    const passwordInput: HTMLInputElement = fixture.nativeElement.querySelector(
      'input[formControlName="password"]',
    );
    passwordInput.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }),
    );
    tick();

    expect(authService.login).toHaveBeenCalledOnceWith({
      email: 'hr@example.com',
      password: 'StrongPass123!',
    });
    expect(authService.getDashboardUrlForRole).toHaveBeenCalledOnceWith('HR');
    expect(router.navigateByUrl).toHaveBeenCalledOnceWith('/dashboard/hr');
  }));

  Object.entries(ROLE_DASHBOARD_PATHS).forEach(([role, dashboardUrl]) => {
    it(`redirects ${role} directly to ${dashboardUrl}`, fakeAsync(() => {
      fillValidForm();
      authService.login.and.returnValue(of(validProfile(role as UserRole)));

      component.onSubmit();
      tick();

      expect(authService.getDashboardUrlForRole).toHaveBeenCalledOnceWith(role as UserRole);
      expect(router.navigateByUrl).toHaveBeenCalledOnceWith(dashboardUrl);
    }));
  });
});
