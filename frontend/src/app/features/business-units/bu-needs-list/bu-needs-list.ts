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

import { BusinessUnitNeed, NeedStatus, NeedPriority, NeedType } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-needs-list',
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
    NgFor,
    NgIf,
    PageHeaderComponent,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './bu-needs-list.html',
  styleUrl: './bu-needs-list.scss',
})
export class BuNeedsList implements OnInit {
  private readonly buService = inject(BusinessUnitService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly displayedColumns = ['title', 'business_unit', 'type', 'status', 'priority', 'created_at', 'actions'];
  
  readonly statuses = Object.values(NeedStatus);
  readonly types = Object.values(NeedType);
  readonly priorities = Object.values(NeedPriority);

  readonly filtersForm = this.formBuilder.nonNullable.group({
    search: [''],
    status: ['' as NeedStatus | ''],
    need_type: ['' as NeedType | ''],
    priority: ['' as NeedPriority | ''],
  });

  needs: BusinessUnitNeed[] = [];
  total = 0;
  pageIndex = 0;
  readonly pageSize = 20;
  isLoading = false;
  errorMessage = '';

  ngOnInit(): void {
    this.loadNeeds();
  }

  loadNeeds(): void {
    this.isLoading = true;
    this.errorMessage = '';
    const filters = {
      ...this.filtersForm.getRawValue(),
      page: this.pageIndex + 1,
    };

    this.buService
      .getNeeds(filters)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        }),
      )
      .subscribe({
        next: (response: any) => {
          this.needs = response.results ?? [];
          this.total = response.count;
        },
        error: (error: any) => {
          this.needs = [];
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
    this.loadNeeds();
  }

  onPageChange(event: PageEvent): void {
    if (event.pageIndex === this.pageIndex) {
      return;
    }
    this.pageIndex = event.pageIndex;
    this.loadNeeds();
  }

  resetFilters(): void {
    this.filtersForm.reset({
      search: '',
      status: '',
      need_type: '',
      priority: '',
    });
    this.pageIndex = 0;
    this.loadNeeds();
  }

  private buildErrorMessage(error: any): string {
    const status = error?.status || 0;
    return `Impossible de charger les besoins. Statut HTTP : ${status}.`;
  }
}
