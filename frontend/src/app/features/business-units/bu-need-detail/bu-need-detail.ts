import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { BusinessUnitNeed } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-need-detail',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, NgIf, PageHeaderComponent, RouterLink],
  templateUrl: './bu-need-detail.html',
  styleUrl: './bu-need-detail.scss',
})
export class BuNeedDetail implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(BusinessUnitService);
  need: BusinessUnitNeed | null = null;
  isLoading = true;
  errorMessage = '';

  ngOnInit(): void {
    const needId = Number(this.route.snapshot.paramMap.get('needId'));
    const businessUnitId = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(needId) || needId <= 0) {
      this.isLoading = false;
      this.errorMessage = 'Besoin invalide.';
      return;
    }
    this.service.getNeed(needId).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: (need) => {
        if (need.business_unit !== businessUnitId) {
          this.errorMessage = "Ce besoin n'appartient pas a la Business Unit demandee.";
          return;
        }
        this.need = need;
      },
      error: (error) => this.errorMessage = error?.status === 404
        ? "Ce besoin n'existe pas ou ne vous est pas accessible."
        : error?.status === 403 ? 'Acces refuse a ce besoin.' : 'Impossible de charger le besoin.',
    });
  }
}
