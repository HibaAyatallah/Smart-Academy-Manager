import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { NgIf } from '@angular/common';
import { AnimateOnScrollDirective } from '../../../shared/directives/animate-on-scroll.directive';

@Component({
  selector: 'app-contact',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatIconModule,
    NgIf,
    AnimateOnScrollDirective
  ],
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.scss'
})
export class ContactComponent {
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly requestTypes = [
    'Candidature',
    'Accès à mon espace',
    'Formation',
    'Collaboration',
    'Client externe',
    'Autre'
  ];

  readonly contactForm = this.fb.nonNullable.group({
    fullName: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    requestType: ['', Validators.required],
    subject: ['', Validators.required],
    message: ['', [Validators.required, Validators.maxLength(1000)]]
  });

  isSubmitting = false;

  submit(): void {
    if (this.contactForm.invalid) {
      this.contactForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;

    // Simulate network delay to show loading state
    setTimeout(() => {
      this.isSubmitting = false;
      
      // As requested, we just show an informative message without creating fake API calls.
      this.snackBar.open('La fonctionnalité d\'envoi est actuellement en cours d\'intégration backend.', 'Compris', {
        duration: 5000,
        panelClass: ['info-snackbar']
      });
      
    }, 800);
  }

  get messageLength(): number {
    return this.contactForm.controls.message.value.length;
  }
}
