import { NgFor, NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, Inject, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { finalize } from 'rxjs/operators';

import {
  ApplicationConversionPayload,
  ApplicationConversionResponse,
  ApplicationConversionType,
} from '../../../../core/models/application.models';
import { BusinessUnit } from '../../../../core/models/business-unit.models';
import { ApplicationService } from '../../../../core/services/application.service';
import {
  BusinessUnitService,
  EligibleSupervisor,
} from '../../../../core/services/business-unit.service';

export interface ConversionDialogData {
  applicationId: number;
  candidateName: string;
  candidateSchool: string;
  conversionType: ApplicationConversionType;
}

type ConversionField = keyof ApplicationConversionPayload;

@Component({
  selector: 'app-conversion-dialog',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    ReactiveFormsModule,
  ],
  templateUrl: './conversion-dialog.component.html',
  styleUrl: './conversion-dialog.component.scss',
})
export class ConversionDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly applicationService = inject(ApplicationService);
  private readonly businessUnitService = inject(BusinessUnitService);
  private readonly dialogRef = inject(MatDialogRef<ConversionDialogComponent>);

  readonly isIntern: boolean;
  readonly form = this.fb.group({
    business_unit: [null as number | null, Validators.required],
    supervisor: [null as number | null],
    school: [''],
    specialization: [''],
    internship_type: [''],
    paid: [false],
    internship_start: [null as string | null],
    internship_end: [null as string | null],
    subject_title: [''],
  });
  businessUnits: BusinessUnit[] = [];
  supervisors: EligibleSupervisor[] = [];
  specificationPdf: File | null = null;
  fieldErrors: Partial<Record<ConversionField, string>> = {};
  generalError = '';
  isLoading = true;
  isSaving = false;

  constructor(@Inject(MAT_DIALOG_DATA) readonly data: ConversionDialogData) {
    this.isIntern = data.conversionType === 'INTERN';
    if (this.isIntern) {
      this.form.controls.supervisor.addValidators(Validators.required);
      this.form.controls.school.setValue(data.candidateSchool || '');
    }
    this.businessUnitService.getBusinessUnits({ is_active: true }).pipe(
      finalize(() => this.isLoading = false),
    ).subscribe({
      next: response => this.businessUnits = response.results,
      error: () => this.generalError = 'Impossible de charger les Business Units.',
    });
    this.form.controls.business_unit.valueChanges.subscribe(id => {
      this.supervisors = [];
      this.form.controls.supervisor.setValue(null);
      if (this.isIntern && id) this.loadSupervisors(id);
    });
  }

  selectSpecification(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.specificationPdf = input.files?.[0] ?? null;
  }

  submit(): void {
    this.fieldErrors = {};
    this.generalError = '';
    if (this.form.invalid || this.isSaving) {
      this.form.markAllAsTouched();
      return;
    }
    const values = this.form.getRawValue();
    const payload: ApplicationConversionPayload = this.isIntern
      ? {
          conversion_type: 'INTERN',
          business_unit: values.business_unit!,
          supervisor: values.supervisor,
          school: values.school || '',
          specialization: values.specialization || '',
          internship_type: values.internship_type || '',
          paid: values.paid || false,
          internship_start: values.internship_start,
          internship_end: values.internship_end,
          subject_title: values.subject_title || '',
          specification_pdf: this.specificationPdf,
        }
      : {
          conversion_type: 'EMPLOYEE',
          business_unit: values.business_unit!,
        };
    this.isSaving = true;
    this.applicationService.convertApplication(this.data.applicationId, payload).pipe(
      finalize(() => this.isSaving = false),
    ).subscribe({
      next: response => this.dialogRef.close(response),
      error: error => this.applyErrors(error),
    });
  }

  private loadSupervisors(businessUnitId: number): void {
    this.businessUnitService.getEligibleSupervisors(businessUnitId).subscribe({
      next: supervisors => this.supervisors = supervisors,
      error: () => this.generalError = 'Impossible de charger les encadrants éligibles.',
    });
  }

  private applyErrors(error: unknown): void {
    const payload = error instanceof HttpErrorResponse ? error.error : null;
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      this.generalError = 'La conversion n’a pas pu être effectuée.';
      return;
    }
    for (const [field, value] of Object.entries(payload as Record<string, unknown>)) {
      const message = Array.isArray(value) ? value.join(' ') : String(value ?? '');
      if (field in this.form.controls || field === 'conversion_type') {
        this.fieldErrors[field as ConversionField] = message;
      } else if (message) {
        this.generalError = message;
      }
    }
    if (!this.generalError && !Object.keys(this.fieldErrors).length) {
      this.generalError = 'La conversion n’a pas pu être effectuée.';
    }
  }
}

