import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
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
import { AuthService } from '../../../core/services/auth.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { BuCreateDialog } from '../bu-create-dialog/bu-create-dialog';

@Component({
  selector: 'app-bu-list',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
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
  private readonly dialog = inject(MatDialog);
  private readonly authService = inject(AuthService);

  get canCreateBusinessUnit(): boolean {
    return this.authService.currentUserSnapshot?.role === 'SUPER_ADMIN';
  }

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

  openCreateDialog(): void {
    if (!this.canCreateBusinessUnit) return;
    this.dialog.open(BuCreateDialog, { width: '560px', maxWidth: '95vw', autoFocus: 'first-tabbable' })
      .afterClosed()
      .subscribe((created: BusinessUnit | undefined) => {
        if (!created) return;
        this.pageIndex = 0;
        this.loadBusinessUnits();
        this.snackBar.open(`La Business Unit « ${created.name} » a été créée.`, 'Fermer', { duration: 4000 });
      });
  }

  private buildErrorMessage(error: any): string {
    const status = error?.status || 0;
    return `Impossible de charger les Business Units. Statut HTTP : ${status}.`;
  }
}
