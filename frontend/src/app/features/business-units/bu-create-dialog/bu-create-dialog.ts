import { NgFor, NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { finalize } from 'rxjs/operators';

import { UserProfile } from '../../../core/models/auth.models';
import { BusinessUnit } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';

type CreateField = 'name' | 'code' | 'manager' | 'is_active';

@Component({
  selector: 'app-bu-create-dialog',
  standalone: true,
  imports: [NgFor, NgIf, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule, ReactiveFormsModule],
  templateUrl: './bu-create-dialog.html',
  styleUrl: './bu-create-dialog.scss',
})
export class BuCreateDialog {
  private readonly formBuilder = inject(FormBuilder);
  private readonly service = inject(BusinessUnitService);
  private readonly dialogRef = inject(MatDialogRef<BuCreateDialog>);
  readonly form = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    code: ['', [Validators.required, Validators.maxLength(50)]],
    manager: [null as number | null],
    is_active: [true, Validators.required],
  });
  managers: UserProfile[] = [];
  fieldErrors: Partial<Record<CreateField, string>> = {};
  generalError = '';
  isSaving = false;

  constructor() {
    this.service.getUsers({ role: 'BU_MANAGER' }).subscribe({
      next: response => this.managers = response.results,
      error: () => this.generalError = 'Impossible de charger la liste des managers. Vous pouvez créer la Business Unit sans manager.',
    });
  }

  submit(): void {
    this.fieldErrors = {};
    this.generalError = '';
    if (this.form.invalid || this.isSaving) {
      this.form.markAllAsTouched();
      if (this.form.invalid) this.generalError = 'Veuillez renseigner les champs obligatoires signalés.';
      return;
    }
    this.isSaving = true;
    this.service.createBusinessUnit(this.form.getRawValue()).pipe(
      finalize(() => this.isSaving = false),
    ).subscribe({
      next: created => this.dialogRef.close(created),
      error: error => this.applyErrors(error),
    });
  }

  private applyErrors(error: unknown): void {
    const payload = error instanceof HttpErrorResponse ? error.error : null;
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      this.generalError = 'La Business Unit n’a pas pu être créée.';
      return;
    }
    for (const [field, value] of Object.entries(payload as Record<string, unknown>)) {
      const message = Array.isArray(value) ? value.join(' ') : String(value ?? '');
      if (field in this.form.controls) this.fieldErrors[field as CreateField] = message;
      else if (message) this.generalError = message;
    }
    if (!this.generalError && !Object.keys(this.fieldErrors).length) {
      this.generalError = 'La Business Unit n’a pas pu être créée.';
    }
  }
}
