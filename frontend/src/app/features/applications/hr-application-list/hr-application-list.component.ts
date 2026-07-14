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

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_TYPE_LABELS,
  Application,
  ApplicationStatus,
  ApplicationType,
} from '../../../core/models/application.models';
import { ApplicationApiError, ApplicationService } from '../../../core/services/application.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-hr-application-list',
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
  templateUrl: './hr-application-list.component.html',
  styleUrl: './hr-application-list.component.scss',
})
export class HrApplicationListComponent implements OnInit {
  private readonly applicationService = inject(ApplicationService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly typeLabels = APPLICATION_TYPE_LABELS;
  readonly statusLabels = APPLICATION_STATUS_LABELS;
  readonly applicationTypes = Object.entries(APPLICATION_TYPE_LABELS).map(([value, label]) => ({
    value: value as ApplicationType,
    label,
  }));
  readonly statuses = Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => ({
    value: value as ApplicationStatus,
    label,
  }));
  readonly displayedColumns = ['candidate', 'type', 'status', 'submitted_at', 'actions'];
  readonly filtersForm = this.formBuilder.nonNullable.group({
    search: [''],
    application_type: ['' as ApplicationType | ''],
    status: ['' as ApplicationStatus | ''],
  });

  applications: Application[] = [];
  total = 0;
  pageIndex = 0;
  readonly pageSize = 20;
  isLoading = false;
  errorMessage = '';

  ngOnInit(): void {
    // The roleGuard already guarantees the profile is loaded and the role
    // is authorised before this component is activated. Calling
    // ensureProfile() here is redundant and introduces a race condition
    // (the component stays on isLoading=true if the Observable does not
    // emit synchronously). Load directly.
    this.loadApplications();
  }

  loadApplications(): void {
    this.isLoading = true;
    this.errorMessage = '';
    const filters = {
      ...this.filtersForm.getRawValue(),
      page: this.pageIndex + 1,
    };
    this.applicationService
      .listApplications(filters)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        }),
      )
      .subscribe({
        next: (response) => {
          this.applications = response.results ?? [];
          this.total = response.count;
        },
        error: (error: ApplicationApiError) => {
          this.applications = [];
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
    this.loadApplications();
  }

  onPageChange(event: PageEvent): void {
    if (event.pageIndex === this.pageIndex) {
      return;
    }
    this.pageIndex = event.pageIndex;
    this.loadApplications();
  }

  resetFilters(): void {
    this.filtersForm.reset({
      search: '',
      application_type: '',
      status: '',
    });
    this.pageIndex = 0;
    this.loadApplications();
  }

  typeLabel(value: ApplicationType): string {
    return APPLICATION_TYPE_LABELS[value];
  }

  statusLabel(value: ApplicationStatus): string {
    return APPLICATION_STATUS_LABELS[value];
  }

  private buildErrorMessage(error: ApplicationApiError): string {
    const status = error?.status || 0;
    return `Impossible de charger les candidatures. Statut HTTP : ${status}.`;
  }


}
