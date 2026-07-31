import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { finalize } from 'rxjs/operators';
import {
  APPLICATION_TYPE_LABELS,
} from '../../../core/models/application.models';
import { OFFER_STATUS_LABELS, Offer } from '../../../core/models/offer.models';
import { AuthService } from '../../../core/services/auth.service';
import { OfferService } from '../../../core/services/offer.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-offer-list',
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
    MatIconModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    PageHeaderComponent,
  ],
  templateUrl: './offer-list.component.html',
  styleUrls: ['./offer-list.component.scss'],
})
export class OfferListComponent implements OnInit {
  private readonly offerService = inject(OfferService);
  private readonly fb = inject(FormBuilder);
  readonly authService = inject(AuthService);

  readonly applicationTypes = Object.entries(APPLICATION_TYPE_LABELS).map(([value, label]) => ({ value, label }));
  readonly statuses = Object.entries(OFFER_STATUS_LABELS).map(([value, label]) => ({ value, label }));

  readonly filtersForm = this.fb.nonNullable.group({
    search: [''],
    status: [''],
  });

  offers: Offer[] = [];
  isLoading = true;
  errorMessage = '';

  // Pagination
  total = 0;
  pageSize = 10;
  pageIndex = 0;

  // Table columns (for admins)
  displayedColumns = ['title', 'type', 'business_unit', 'status', 'publication_date', 'actions'];

  get isCandidate(): boolean {
    return this.authService.currentUserSnapshot?.role === 'CANDIDATE';
  }

  get isAdmin(): boolean {
    const role = this.authService.currentUserSnapshot?.role;
    return role === 'SUPER_ADMIN';
  }

  ngOnInit(): void {
    if (this.isCandidate) {
      // Candidates only see published offers
      this.filtersForm.patchValue({ status: 'PUBLISHED' });
    }
    this.loadOffers();
  }

  loadOffers(page = 1): void {
    this.isLoading = true;
    this.errorMessage = '';

    const formValue = this.filtersForm.getRawValue();
    const filters: any = { page };

    if (formValue.search) filters.search = formValue.search;
    if (formValue.status) filters.status = formValue.status;

    this.offerService
      .getOffers(filters)
      .pipe(finalize(() => (this.isLoading = false)))
      .subscribe({
        next: (res) => {
          this.offers = res.results;
          this.total = res.count;
          this.pageIndex = page - 1;
        },
        error: () => {
          this.errorMessage = 'Une erreur est survenue lors du chargement des offres.';
        },
      });
  }

  applyFilters(): void {
    this.loadOffers(1);
  }

  resetFilters(): void {
    this.filtersForm.reset();
    if (this.isCandidate) {
      this.filtersForm.patchValue({ status: 'PUBLISHED' });
    }
    this.loadOffers(1);
  }

  onPageChange(event: PageEvent): void {
    this.pageSize = event.pageSize;
    this.loadOffers(event.pageIndex + 1);
  }

  typeLabel(type: any): string {
    return APPLICATION_TYPE_LABELS[type as keyof typeof APPLICATION_TYPE_LABELS] || type;
  }

  statusLabel(status: any): string {
    return OFFER_STATUS_LABELS[status as keyof typeof OFFER_STATUS_LABELS] || status;
  }
}
