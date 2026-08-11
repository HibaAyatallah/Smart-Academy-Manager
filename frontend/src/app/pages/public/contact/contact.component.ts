import { NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';

import { ContactService } from '../../../core/services/contact.service';
import { AnimateOnScrollDirective } from '../../../shared/directives/animate-on-scroll.directive';

@Component({
  selector: 'app-contact',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatSnackBarModule, MatIconModule, NgIf, AnimateOnScrollDirective],
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.scss',
})
export class ContactComponent {
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly contactService = inject(ContactService);

  readonly requestTypes = ['Candidature', 'Accès à mon espace', 'Formation', 'Collaboration', 'Client externe', 'Autre'];
  readonly contactForm = this.fb.nonNullable.group({
    fullName: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    email: ['', [Validators.required, Validators.email]],
    requestType: ['', Validators.required],
    subject: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(200)]],
    message: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
  });
  isSubmitting = false;

  submit(): void {
    if (this.contactForm.invalid || this.isSubmitting) {
      this.contactForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    const value = this.contactForm.getRawValue();
    this.contactService.submit({
      full_name: value.fullName, email: value.email, request_type: value.requestType,
      subject: value.subject, message: value.message,
    }).pipe(finalize(() => this.isSubmitting = false)).subscribe({
      next: () => {
        this.contactForm.reset();
        this.snackBar.open('Votre message a bien été envoyé.', 'Fermer', {
          duration: 5000, panelClass: ['success-snackbar'],
        });
      },
      error: (error) => {
        const message = error.status === 429
          ? 'Trop de messages ont été envoyés. Veuillez réessayer plus tard.'
          : error.error?.detail ?? 'L’envoi a échoué. Veuillez réessayer.';
        this.snackBar.open(message, 'Fermer', { duration: 6000, panelClass: ['error-snackbar'] });
      },
    });
  }

  get messageLength(): number {
    return this.contactForm.controls.message.value.length;
  }
}
