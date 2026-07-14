import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { BusinessUnit } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-list',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    NgIf,
    PageHeaderComponent,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './bu-list.html',
  styleUrl: './bu-list.scss',
})
export class BuList implements OnInit {
  private readonly buService = inject(BusinessUnitService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly displayedColumns = ['name', 'code', 'manager', 'status', 'created_at', 'actions'];
  readonly filtersForm = this.formBuilder.nonNullable.group({
    search: [''],
    is_active: ['' as boolean | ''],
  });

  businessUnits: BusinessUnit[] = [];
  total = 0;
  pageIndex = 0;
  readonly pageSize = 20;
  isLoading = false;
  errorMessage = '';

  ngOnInit(): void {
    this.loadBusinessUnits();
  }

  loadBusinessUnits(): void {
    this.isLoading = true;
    this.errorMessage = '';
    const filters = {
      ...this.filtersForm.getRawValue(),
      page: this.pageIndex + 1,
    };

    this.buService
      .getBusinessUnits(filters)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        }),
      )
      .subscribe({
        next: (response: any) => {
          this.businessUnits = response.results ?? [];
          this.total = response.count;
        },
        error: (error: any) => {
          this.businessUnits = [];
          this.total = 0;
          this.errorMessage = this.buildErrorMessage(error);
          this.snackBar.open(this.errorMessage, 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  applyFilters(): void {
    this.pageIndex = 0;
    this.loadBusinessUnits();
  }

  onPageChange(event: PageEvent): void {
    if (event.pageIndex === this.pageIndex) {
      return;
    }
    this.pageIndex = event.pageIndex;
    this.loadBusinessUnits();
  }

  resetFilters(): void {
    this.filtersForm.reset({
      search: '',
      is_active: '',
    });
    this.pageIndex = 0;
    this.loadBusinessUnits();
  }

  private buildErrorMessage(error: any): string {
    const status = error?.status || 0;
    return `Impossible de charger les Business Units. Statut HTTP : ${status}.`;
  }
}
