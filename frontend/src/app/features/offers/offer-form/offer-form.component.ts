import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, isDevMode } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DATE_LOCALE, MatNativeDateModule, provideNativeDateAdapter } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, switchMap, of } from 'rxjs';

import { APPLICATION_TYPE_LABELS, EDUCATION_LEVEL_LABELS } from '../../../core/models/application.models';
import { OfferCreateUpdate } from '../../../core/models/offer.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { OfferService } from '../../../core/services/offer.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { minTodayValidator, dateRangeValidator } from '../../../core/utils/date-validators';

@Component({
  selector: 'app-offer-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSnackBarModule,
    PageHeaderComponent,
  ],
  templateUrl: './offer-form.component.html',
  styleUrls: ['./offer-form.component.scss'],
  providers: [
    { provide: MAT_DATE_LOCALE, useValue: 'fr-FR' },
    provideNativeDateAdapter(),
  ],
})
export class OfferFormComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly offerService = inject(OfferService);
  private readonly buService = inject(BusinessUnitService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  isEditing = false;
  offerId: number | null = null;
  isLoading = false;
  today = (() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  })();

  businessUnits: any[] = [];
  
  readonly applicationTypes = Object.entries(APPLICATION_TYPE_LABELS).map(([value, label]) => ({ value, label }));
  readonly educationLevels = Object.entries(EDUCATION_LEVEL_LABELS).map(([value, label]) => ({ value, label }));

  form = this.fb.group({
    title: ['', [Validators.required, Validators.maxLength(255)]],
    description: ['', [Validators.required]],
    business_unit: [null as number | null, [Validators.required]],
    application_type: ['', [Validators.required]],
    required_skills: [''],
    required_level: [''],
    number_of_positions: [1, [Validators.min(1)]],
    location: ['', [Validators.maxLength(255)]],
    start_date: [null as string | Date | null, [minTodayValidator()]],
    end_date: [null as string | Date | null, [minTodayValidator()]],
    application_deadline: [null as string | Date | null, [minTodayValidator()]],
  }, {
    validators: [dateRangeValidator('start_date', 'end_date')]
  });

  ngOnInit(): void {
    this.isLoading = true;
    
    // Charger les BUs d'abord
    this.buService.getBusinessUnits().pipe(
      switchMap(buResponse => {
        this.businessUnits = buResponse.results;
        
        // Vérifier si on est en mode édition
        const idParam = this.route.snapshot.paramMap.get('id');
        if (idParam) {
          this.isEditing = true;
          this.offerId = Number(idParam);
          return this.offerService.getOffer(this.offerId);
        }
        return of(null);
      }),
      finalize(() => this.isLoading = false)
    ).subscribe({
      next: (offer) => {
        if (offer) {
          this.form.patchValue({
            title: offer.title,
            description: offer.description,
            business_unit: offer.business_unit,
            application_type: offer.application_type,
            required_skills: offer.required_skills,
            required_level: offer.required_level,
            number_of_positions: offer.number_of_positions,
            location: offer.location,
            start_date: offer.start_date,
            end_date: offer.end_date,
            application_deadline: offer.application_deadline,
          });
        }
      },
      error: () => {
        this.snackBar.open('Erreur lors du chargement des données.', 'Fermer', { duration: 3000 });
        this.router.navigate(['/offers']);
      }
    });
  }

  onSubmit(): void {
    this.clearApiDateErrors();
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    const data = this.form.value as OfferCreateUpdate;

    const request$ = this.isEditing && this.offerId
      ? this.offerService.updateOffer(this.offerId, data)
      : this.offerService.createOffer(data);

    request$.pipe(
      finalize(() => this.isLoading = false)
    ).subscribe({
      next: (offer) => {
        this.snackBar.open(`Offre ${this.isEditing ? 'modifiée' : 'créée'} avec succès.`, 'Fermer', { duration: 3000 });
        this.router.navigate(['/offers', offer.id]);
      },
      error: (err) => {
        if (isDevMode()) console.error(`[Offers] Save failed (status=${err?.status ?? 'unknown'}).`);
        const hasDateErrors = this.applyApiDateErrors(err);
        this.snackBar.open(
          hasDateErrors ? 'Veuillez corriger les dates signalées.' : "Erreur lors de la sauvegarde de l'offre.",
          'Fermer', { duration: 4000 },
        );
      }
    });
  }

  apiDateError(field: 'start_date' | 'end_date' | 'application_deadline'): string {
    return this.form.controls[field].getError('api') || '';
  }

  private clearApiDateErrors(): void {
    for (const field of ['start_date', 'end_date', 'application_deadline'] as const) {
      const control = this.form.controls[field];
      if (!control.errors?.['api']) continue;
      const { api, ...otherErrors } = control.errors;
      control.setErrors(Object.keys(otherErrors).length ? otherErrors : null);
    }
  }

  private applyApiDateErrors(error: unknown): boolean {
    const payload = error instanceof HttpErrorResponse ? error.error : error && typeof error === 'object' ? (error as any).error : null;
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    let applied = false;
    for (const field of ['start_date', 'end_date', 'application_deadline'] as const) {
      if (!(field in payload)) continue;
      const value = payload[field];
      const message = Array.isArray(value) ? value.join(' ') : String(value ?? '');
      if (!message) continue;
      const control = this.form.controls[field];
      control.setErrors({ ...control.errors, api: message });
      control.markAsTouched();
      applied = true;
    }
    return applied;
  }
}
