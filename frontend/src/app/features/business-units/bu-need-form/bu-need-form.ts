import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { finalize } from 'rxjs/operators';

import {
  BusinessUnit,
  BusinessUnitMembership,
  BusinessUnitNeed,
  NeedPriority,
  NeedType,
} from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-need-form',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    NgFor,
    NgIf,
    PageHeaderComponent,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './bu-need-form.html',
  styleUrl: './bu-need-form.scss',
})
export class BuNeedForm implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(BusinessUnitService);
  private readonly snackBar = inject(MatSnackBar);

  readonly needTypes = Object.values(NeedType);
  readonly priorities = Object.values(NeedPriority);
  readonly form = this.formBuilder.nonNullable.group({
    business_unit: [0, [Validators.required, Validators.min(1)]],
    title: ['', [Validators.required, Validators.maxLength(255)]],
    description: ['', Validators.required],
    need_type: [NeedType.RECRUITMENT_INTERNSHIP, Validators.required],
    requester: [null as number | null],
    training_audience: ['ALL' as 'ALL' | 'SPECIFIC'],
    specific_recipient_emails: [''],
    priority: [NeedPriority.MEDIUM, Validators.required],
    expected_date: [''],
  });

  managedBusinessUnits: BusinessUnit[] = [];
  collaborators: BusinessUnitMembership[] = [];
  needId: number | null = null;
  isLoading = true;
  isSaving = false;
  errorMessage = '';

  get isEditMode(): boolean {
    return this.needId !== null;
  }

  get isTraining(): boolean {
    return this.form.controls.need_type.value === NeedType.TRAINING;
  }

  get isSpecificAudience(): boolean {
    return this.isTraining && this.form.controls.training_audience.value === 'SPECIFIC';
  }

  ngOnInit(): void {
    const rawNeedId = this.route.snapshot.paramMap.get('needId');
    this.needId = rawNeedId ? Number(rawNeedId) : null;
    if (this.needId !== null && (!Number.isInteger(this.needId) || this.needId <= 0)) {
      this.isLoading = false;
      this.errorMessage = 'Besoin invalide.';
      return;
    }

    const needRequest = this.needId === null ? of(null) : this.service.getNeed(this.needId);
    forkJoin({
      businessUnits: this.service.getBusinessUnits({ is_active: true }),
      memberships: this.service.getMemberships({ is_active: true }),
      need: needRequest,
    }).pipe(
      finalize(() => this.isLoading = false),
    ).subscribe({
      next: ({ businessUnits, memberships, need }) => {
        this.collaborators = memberships.results ?? [];
        this.initializeForm(businessUnits.results ?? [], need);
      },
      error: (error) => this.errorMessage = this.apiErrorMessage(error, 'Impossible de préparer le formulaire.'),
    });
  }

  save(): void {
    if (this.form.invalid || this.isSaving || this.isLoading) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    if (!this.managedBusinessUnits.some((businessUnit) => businessUnit.id === value.business_unit)) {
      this.errorMessage = 'La Business Unit sélectionnée ne vous est pas accessible.';
      return;
    }
    const specificEmails = value.specific_recipient_emails
      .split(/[;,\n]/)
      .map(email => email.trim())
      .filter(Boolean);
    if (this.isSpecificAudience && !specificEmails.length) {
      this.errorMessage = 'Saisissez au moins un email appartenant à votre Business Unit.';
      return;
    }

    const payload: Partial<BusinessUnitNeed> = {
      ...value,
      expected_date: value.expected_date || null,
      specific_recipient_emails: this.isSpecificAudience ? specificEmails : [],
    };
    const request = this.needId === null
      ? this.service.createNeed(payload)
      : this.service.updateNeed(this.needId, payload);

    this.isSaving = true;
    this.errorMessage = '';
    request.pipe(
      finalize(() => this.isSaving = false),
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.isEditMode ? 'Besoin modifié avec succès.' : 'Besoin créé avec succès.',
          'Fermer',
          { duration: 3500 },
        );
        void this.router.navigateByUrl('/business-units/needs');
      },
      error: (error) => this.errorMessage = this.apiErrorMessage(error, "Le besoin n'a pas pu être enregistré."),
    });
  }

  private initializeForm(businessUnits: BusinessUnit[], need: BusinessUnitNeed | null): void {
    this.managedBusinessUnits = businessUnits;
    if (!businessUnits.length) {
      this.errorMessage = 'Aucune Business Unit active ne vous est assignée.';
      return;
    }

    if (!need) {
      if (businessUnits.length === 1) {
        this.form.controls.business_unit.setValue(businessUnits[0].id);
      }
      return;
    }

    if (!businessUnits.some((businessUnit) => businessUnit.id === need.business_unit)) {
      this.errorMessage = "Ce besoin n'appartient pas à une Business Unit que vous gérez.";
      this.form.disable();
      return;
    }

    this.form.setValue({
      business_unit: need.business_unit,
      title: need.title,
      description: need.description,
      need_type: need.need_type,
      requester: need.requester ?? null,
      training_audience: need.training_audience ?? 'ALL',
      specific_recipient_emails: (need.training_recipient_emails ?? []).join(', '),
      priority: need.priority,
      expected_date: need.expected_date ?? '',
    });
  }

  private apiErrorMessage(error: any, fallback: string): string {
    const body = error?.error;
    if (body && typeof body === 'object') {
      const messages = Object.values(body).flat().map(String).filter(Boolean);
      if (messages.length) return messages.join(' ');
    }
    if (error?.status === 403) return 'Vous n’avez pas la permission de gérer ce besoin.';
    if (error?.status === 404) return "Ce besoin n'existe pas ou ne vous est pas accessible.";
    return fallback;
  }
}
