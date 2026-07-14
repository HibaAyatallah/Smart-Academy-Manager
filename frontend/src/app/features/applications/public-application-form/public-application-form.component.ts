import { NgFor, NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatStepperModule } from '@angular/material/stepper';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import {
  APPLICATION_TYPE_LABELS,
  ApplicationType,
  EDUCATION_LEVEL_LABELS,
  EducationLevel,
} from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';

type RequiredFileTarget = 'cv' | 'cover' | 'photo';
type ApplicationFormField =
  | 'email'
  | 'password'
  | 'first_name'
  | 'last_name'
  | 'phone_number'
  | 'current_school'
  | 'study_level'
  | 'study_level_other'
  | 'study_field'
  | 'linkedin_url'
  | 'portfolio_url'
  | 'address'
  | 'application_type'
  | 'motivation_message';

const FILE_RULES: Record<
  RequiredFileTarget,
  { label: string; extensions: string[]; mimeTypes: string[]; maxSizeMb: number }
> = {
  cv: {
    label: 'CV',
    extensions: ['.pdf', '.doc', '.docx'],
    mimeTypes: [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ],
    maxSizeMb: 5,
  },
  cover: {
    label: 'Lettre de motivation',
    extensions: ['.pdf', '.doc', '.docx'],
    mimeTypes: [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ],
    maxSizeMb: 5,
  },
  photo: {
    label: 'Photo personnelle',
    extensions: ['.jpg', '.jpeg', '.png'],
    mimeTypes: ['image/jpeg', 'image/png'],
    maxSizeMb: 3,
  },
};

const FILE_SIGNATURES: Record<string, number[][]> = {
  '.pdf': [[0x25, 0x50, 0x44, 0x46]],
  '.doc': [[0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1]],
  '.docx': [[0x50, 0x4b]],
  '.jpg': [[0xff, 0xd8, 0xff]],
  '.jpeg': [[0xff, 0xd8, 0xff]],
  '.png': [[0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]],
};

@Component({
  selector: 'app-public-application-form',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatIconModule,
    MatStepperModule,
    NgFor,
    NgIf,
    ReactiveFormsModule,
  ],
  templateUrl: './public-application-form.component.html',
  styleUrl: './public-application-form.component.scss',
})
export class PublicApplicationFormComponent {
  private readonly applicationService = inject(ApplicationService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly applicationTypes = Object.entries(APPLICATION_TYPE_LABELS).map(([value, label]) => ({
    value: value as ApplicationType,
    label,
  }));
  readonly educationLevels = Object.entries(EDUCATION_LEVEL_LABELS).map(([value, label]) => ({
    value: value as EducationLevel,
    label,
  }));
  readonly fileRules = FILE_RULES;

  readonly form = this.formBuilder.group({
    personal: this.formBuilder.nonNullable.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      phone_number: ['', Validators.required],
      address: [''],
    }),
    academic: this.formBuilder.nonNullable.group({
      current_school: ['', Validators.required],
      study_level: ['' as EducationLevel | '', Validators.required],
      study_level_other: [''],
      study_field: ['', Validators.required],
    }),
    professional: this.formBuilder.nonNullable.group({
      application_type: ['PFA_INTERNSHIP' as ApplicationType, Validators.required],
      linkedin_url: [''],
      portfolio_url: [''],
      motivation_message: [''],
    })
  });

  cvFile: File | null = null;
  coverLetterFile: File | null = null;
  personalPhotoFile: File | null = null;
  fileErrors: Record<RequiredFileTarget, string> = {
    cv: '',
    cover: '',
    photo: '',
  };
  apiFieldErrors: Partial<Record<ApplicationFormField, string>> = {};
  generalError = '';
  isSubmitting = false;

  constructor() {
    this.form.controls.academic.controls.study_level.valueChanges.subscribe((value) => {
      const otherControl = this.form.controls.academic.controls.study_level_other;
      if (value === 'OTHER') {
        otherControl.addValidators(Validators.required);
      } else {
        otherControl.clearValidators();
        otherControl.setValue('');
      }
      otherControl.updateValueAndValidity();
    });
  }

  async onFileSelected(event: Event, target: RequiredFileTarget): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = Array.from(input.files ?? [])[0] ?? null;
    const error = await this.validateFile(file, target);

    this.fileErrors[target] = error;
    if (error) {
      this.setFile(target, null);
      input.value = '';
      return;
    }

    this.setFile(target, file);
  }

  removeFile(target: RequiredFileTarget, input: HTMLInputElement): void {
    this.setFile(target, null);
    this.fileErrors[target] = '';
    input.value = '';
  }

  submit(): void {
    this.clearApiErrors();
    this.validateRequiredFiles();
    if (this.form.invalid || this.hasFileErrors() || this.isSubmitting) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    const formData = this.buildFormData();

    this.applicationService
      .submitPublicApplication(formData)
      .pipe(
        finalize(() => {
          this.isSubmitting = false;
        }),
      )
      .subscribe({
        next: () => {
          this.snackBar.open('Candidature déposée avec succès.', 'Fermer', {
            duration: 4000,
          });
          void this.router.navigateByUrl('/connexion');
        },
        error: (error: unknown) => {
          this.applyApiErrors(error);
          this.snackBar.open(this.generalError || 'La candidature n a pas pu etre envoyée.', 'Fermer', {
            duration: 5000,
          });
        },
      });
  }

  fieldHasError(groupName: 'personal' | 'academic' | 'professional', fieldName: string): boolean {
    const group = this.form.controls[groupName] as any;
    const control = group.controls[fieldName];
    return control.invalid && (control.dirty || control.touched);
  }

  apiError(fieldName: ApplicationFormField): string {
    return this.apiFieldErrors[fieldName] ?? '';
  }

  private setFile(target: RequiredFileTarget, file: File | null): void {
    if (target === 'cv') {
      this.cvFile = file;
    } else if (target === 'cover') {
      this.coverLetterFile = file;
    } else {
      this.personalPhotoFile = file;
    }
  }

  private validateRequiredFiles(): void {
    this.fileErrors.cv = this.cvFile ? this.fileErrors.cv : this.requiredFileMessage('cv');
    this.fileErrors.cover = this.coverLetterFile
      ? this.fileErrors.cover
      : this.requiredFileMessage('cover');
    this.fileErrors.photo = this.personalPhotoFile
      ? this.fileErrors.photo
      : this.requiredFileMessage('photo');
  }

  private async validateFile(file: File | null, target: RequiredFileTarget): Promise<string> {
    if (!file) {
      return this.requiredFileMessage(target);
    }
    if (file.name.length > 255) {
      return 'Nom de fichier trop long.';
    }
    const extension = this.fileExtension(file.name);
    if (!FILE_RULES[target].extensions.includes(extension)) {
      return `Format non autorisé. Utilisez ${FILE_RULES[target].extensions.join(', ')}.`;
    }
    if (!FILE_RULES[target].mimeTypes.includes(file.type)) {
      return 'Type de fichier non autorisé.';
    }
    if (file.size > FILE_RULES[target].maxSizeMb * 1024 * 1024) {
      if (target === 'photo') {
        return `La photo ne doit pas dépasser ${FILE_RULES[target].maxSizeMb} Mo.`;
      }
      return `${FILE_RULES[target].label} trop volumineux. Taille maximale : ${FILE_RULES[target].maxSizeMb} Mo.`;
    }
    if (!(await this.fileMatchesSignature(file, extension))) {
      return 'Le contenu du fichier ne correspond pas au format annoncé.';
    }
    return '';
  }

  private async fileMatchesSignature(file: File, extension: string): Promise<boolean> {
    const signatures = FILE_SIGNATURES[extension];
    if (!signatures) {
      return true;
    }

    try {
      const header = new Uint8Array(await file.slice(0, 16).arrayBuffer());
      return signatures.some((signature) =>
        signature.every((byte, index) => header[index] === byte),
      );
    } catch {
      return false;
    }
  }

  private fileExtension(fileName: string): string {
    const index = fileName.lastIndexOf('.');
    return index >= 0 ? fileName.slice(index).toLowerCase() : '';
  }

  private hasFileErrors(): boolean {
    return Object.values(this.fileErrors).some(Boolean);
  }

  private clearApiErrors(): void {
    this.apiFieldErrors = {};
    this.generalError = '';
  }

  private applyApiErrors(error: unknown): void {
    const payload = error instanceof HttpErrorResponse ? error.error : null;
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      this.generalError = this.errorMessage(payload) || 'La candidature n a pas pu etre envoyée.';
      return;
    }

    const generalMessages: string[] = [];
    for (const [field, value] of Object.entries(payload as Record<string, unknown>)) {
      const message = this.errorMessage(value);
      if (!message) {
        continue;
      }

      if (field === 'cv') {
        this.fileErrors.cv = message;
      } else if (field === 'cover_letter') {
        this.fileErrors.cover = message;
      } else if (field === 'personal_photo') {
        this.fileErrors.photo = message;
      } else if (this.isApplicationFormField(field)) {
        this.apiFieldErrors[field] = message;
      } else {
        generalMessages.push(message);
      }
    }

    this.generalError = generalMessages.join(' ');
    if (!this.generalError && !Object.keys(this.apiFieldErrors).length && !this.hasFileErrors()) {
      this.generalError = 'La candidature n a pas pu etre envoyée.';
    }
  }

  private isApplicationFormField(field: string): field is ApplicationFormField {
    return field in this.form.controls.personal.controls || 
           field in this.form.controls.academic.controls || 
           field in this.form.controls.professional.controls;
  }

  private errorMessage(value: unknown): string {
    if (Array.isArray(value)) {
      return value.map(String).join(' ');
    }
    return typeof value === 'string' ? value : '';
  }

  private requiredFileMessage(target: RequiredFileTarget): string {
    if (target === 'cv') {
      return 'Le CV est obligatoire.';
    }
    if (target === 'cover') {
      return 'La lettre de motivation est obligatoire.';
    }
    return 'La photo personnelle est obligatoire.';
  }

  private buildFormData(): FormData {
    const formData = new FormData();
    const value = this.form.getRawValue();
    
    Object.entries(value.personal).forEach(([key, fieldValue]) => {
      formData.append(key, String(fieldValue ?? ''));
    });
    Object.entries(value.academic).forEach(([key, fieldValue]) => {
      formData.append(key, String(fieldValue ?? ''));
    });
    Object.entries(value.professional).forEach(([key, fieldValue]) => {
      formData.append(key, String(fieldValue ?? ''));
    });

    if (this.cvFile) {
      formData.append('cv', this.cvFile);
    }
    if (this.coverLetterFile) {
      formData.append('cover_letter', this.coverLetterFile);
    }
    if (this.personalPhotoFile) {
      formData.append('personal_photo', this.personalPhotoFile);
    }
    return formData;
  }
}
