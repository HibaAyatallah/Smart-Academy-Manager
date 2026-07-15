import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { BusinessUnitNeed } from '../../../core/models/business-unit.models';
import { UserProfile } from '../../../core/models/auth.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { AuthService } from '../../../core/services/auth.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-need-detail',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, MatFormFieldModule, MatInputModule, MatSelectModule, NgFor, NgIf, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './bu-need-detail.html',
  styleUrl: './bu-need-detail.scss',
})
export class BuNeedDetail implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(BusinessUnitService);
  private readonly authService = inject(AuthService, { optional: true });
  private readonly formBuilder = inject(FormBuilder);
  readonly canManageNeeds = this.authService?.currentUserSnapshot?.role === 'BU_MANAGER';
  readonly canDecide = this.authService?.currentUserSnapshot?.role === 'SUPER_ADMIN';
  readonly decisionForm = this.formBuilder.nonNullable.group({
    decision_comment: ['', Validators.required],
    training_start_date: [''],
    training_end_date: [''],
    training_link: [''],
    trainer: [0],
  });
  trainers: UserProfile[] = [];
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
        this.decisionForm.patchValue({
          decision_comment: need.decision_comment ?? '',
          training_start_date: need.training_start_date ?? '',
          training_end_date: need.training_end_date ?? '',
          training_link: need.training_link ?? '',
          trainer: need.trainer ?? 0,
        });
        if (this.canDecide) {
          this.service.getUsers().subscribe({
            next: response => this.trainers = (response.results ?? []).filter(user => user.role === 'TRAINER_TUTOR'),
          });
        }
      },
      error: (error) => this.errorMessage = error?.status === 404
        ? "Ce besoin n'existe pas ou ne vous est pas accessible."
        : error?.status === 403 ? 'Acces refuse a ce besoin.' : 'Impossible de charger le besoin.',
    });
  }

  decide(status: 'CONFIRMED' | 'REFUSED'): void {
    if (!this.need || this.decisionForm.controls.decision_comment.invalid) {
      this.decisionForm.markAllAsTouched();
      return;
    }
    const values = this.decisionForm.getRawValue();
    const payload: Partial<BusinessUnitNeed> = {
      status: status as any,
      decision_comment: values.decision_comment,
    };
    if (status === 'CONFIRMED' && this.need.need_type === 'TRAINING') {
      Object.assign(payload, {
        training_start_date: values.training_start_date || null,
        training_end_date: values.training_end_date || null,
        training_link: values.training_link,
        trainer: values.trainer || null,
      });
    }
    this.service.updateNeed(this.need.id, payload).subscribe({
      next: need => this.need = need,
      error: error => this.errorMessage = Object.values(error?.error ?? {}).flat().join(' ') || 'Impossible de traiter ce besoin.',
    });
  }
}
