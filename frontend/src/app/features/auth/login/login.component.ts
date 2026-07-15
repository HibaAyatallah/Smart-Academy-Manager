import { HttpErrorResponse } from '@angular/common/http';
import { NgIf } from '@angular/common';
import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { RouterLink } from '@angular/router';
import { TimeoutError, timeout } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    NgIf,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private static readonly loginTimeoutMs = 10_000;
  private readonly authService = inject(AuthService);
  private readonly changeDetectorRef = inject(ChangeDetectorRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  isSubmitting = false;
  errorMessage = '';
  hidePassword = true;

  onSubmit(): void {
    if (this.loginForm.invalid || this.isSubmitting) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    this.authService
      .login(this.loginForm.getRawValue())
      .pipe(
        timeout(LoginComponent.loginTimeoutMs),
        finalize(() => {
          this.isSubmitting = false;
          this.changeDetectorRef.markForCheck();
        }),
      )
      .subscribe({
        next: (profile) => {
          const dashboardUrl = this.authService.getDashboardUrlForRole(profile.role);
          void this.router.navigateByUrl(dashboardUrl);
        },
        error: (error: unknown) => {
          console.error('[Auth] Échec de connexion.');
          this.errorMessage = this.resolveErrorMessage(error);
        },
      });
  }

  private resolveErrorMessage(error: unknown): string {
    if (error instanceof TimeoutError) {
      return 'Le backend ne répond pas. Vérifiez qu\'il est bien démarré.';
    }
    if (!(error instanceof HttpErrorResponse)) {
      return 'La connexion a échoué. Réessayez dans un instant.';
    }
    if (error.status === 401) {
      return 'Email ou mot de passe incorrect.';
    }
    if (error.status === 0) {
      return 'Impossible de joindre le backend. Vérifiez qu\'il est bien démarré.';
    }
    return 'La connexion a échoué. Réessayez dans un instant.';
  }
}
