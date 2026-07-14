import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { BusinessUnit } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-detail',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, NgIf, PageHeaderComponent, RouterLink],
  templateUrl: './bu-detail.html',
  styleUrl: './bu-detail.scss',
})
export class BuDetail implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(BusinessUnitService);

  businessUnit: BusinessUnit | null = null;
  isLoading = true;
  errorMessage = '';

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(id) || id <= 0) {
      this.isLoading = false;
      this.errorMessage = 'Business Unit invalide.';
      return;
    }
    this.service.getBusinessUnit(id).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: (businessUnit) => this.businessUnit = businessUnit,
      error: (error) => this.errorMessage = this.errorForStatus(error?.status),
    });
  }

  private errorForStatus(status: number): string {
    if (status === 403) return 'Acces refuse a cette Business Unit.';
    if (status === 404) return "Cette Business Unit n'existe pas ou ne vous est pas accessible.";
    return 'Impossible de charger la Business Unit.';
  }
}
