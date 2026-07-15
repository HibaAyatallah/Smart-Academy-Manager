import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { finalize } from 'rxjs/operators';

import { BusinessUnitNeed, NeedStatus, NeedType } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-employee-trainings',
  standalone: true,
  imports: [DatePipe, MatCardModule, MatProgressSpinnerModule, MatTableModule, NgIf, PageHeaderComponent],
  templateUrl: './employee-trainings.html',
  styleUrl: './employee-trainings.scss',
})
export class EmployeeTrainings implements OnInit {
  private readonly service = inject(BusinessUnitService);

  readonly displayedColumns = ['title', 'type', 'training_start_date', 'training_end_date', 'training_link'];
  trainings: BusinessUnitNeed[] = [];
  isLoading = true;
  errorMessage = '';

  ngOnInit(): void {
    this.service.getNeeds({
      need_type: NeedType.TRAINING,
      status: NeedStatus.CONFIRMED,
    }).pipe(
      finalize(() => this.isLoading = false),
    ).subscribe({
      next: response => this.trainings = response.results ?? [],
      error: () => this.errorMessage = 'Impossible de charger les formations de votre Business Unit.',
    });
  }
}
