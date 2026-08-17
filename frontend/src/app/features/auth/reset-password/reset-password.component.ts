import { NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { AuthService } from '../../../core/services/auth.service';

function matchingPasswords(control: AbstractControl): ValidationErrors | null {
  return control.get('new_password')?.value === control.get('confirmation')?.value ? null : { passwordMismatch: true };
}

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [NgIf, ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss',
})
export class ResetPasswordComponent {
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly formBuilder = inject(FormBuilder);
  private readonly tokenParts = (this.route.snapshot.queryParamMap.get('token') ?? '').split('.', 2);
  readonly uid = this.tokenParts.length === 2 ? this.tokenParts[0] : '';
  readonly token = this.tokenParts.length === 2 ? this.tokenParts[1] : '';
  readonly form = this.formBuilder.nonNullable.group({
    new_password: ['', Validators.required],
    confirmation: ['', Validators.required],
  }, { validators: matchingPasswords });

  validating = true;
  validToken = false;
  submitting = false;
  success = false;
  errorMessage = '';
  hidePassword = true;
  hideConfirmation = true;

  constructor() {
    if (!this.uid || !this.token) {
      this.validating = false;
      return;
    }
    this.authService.validatePasswordResetToken(this.uid, this.token)
      .pipe(finalize(() => this.validating = false))
      .subscribe({ next: ({ valid }) => this.validToken = valid, error: () => this.validToken = false });
  }

  submit(): void {
    if (this.form.invalid || this.submitting || !this.validToken) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting = true;
    this.errorMessage = '';
    this.authService.confirmPasswordReset({ uid: this.uid, token: this.token, ...this.form.getRawValue() })
      .pipe(finalize(() => this.submitting = false))
      .subscribe({
        next: () => { this.success = true; this.validToken = false; },
        error: (error: unknown) => this.handleError(error),
      });
  }

  private handleError(error: unknown): void {
    if (error instanceof HttpErrorResponse && error.status === 400) {
      const body = error.error as Record<string, string[] | string>;
      const value = body['new_password'] ?? body['confirmation'] ?? body['non_field_errors'];
      this.errorMessage = Array.isArray(value) ? value.join(' ') : value || 'Ce lien est invalide ou expiré.';
      if (body['non_field_errors']) this.validToken = false;
      return;
    }
    this.errorMessage = 'La modification a échoué. Veuillez réessayer.';
  }
}
