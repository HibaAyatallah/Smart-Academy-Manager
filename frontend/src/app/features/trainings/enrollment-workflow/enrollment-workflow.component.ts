import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';
import { ENROLLMENT_STATUS_LABELS, TrainingEnrollment } from '../../../core/models/training.models';
import { AuthService } from '../../../core/services/auth.service';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({ selector: 'app-enrollment-workflow', standalone: true, imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatCardModule, MatChipsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatSnackBarModule, PageHeaderComponent], templateUrl: './enrollment-workflow.component.html', styleUrl: './enrollment-workflow.component.scss' })
export class EnrollmentWorkflowComponent implements OnInit {
  private readonly service = inject(TrainingService); private readonly auth = inject(AuthService); private readonly fb = inject(FormBuilder); private readonly snack = inject(MatSnackBar);
  readonly labels = ENROLLMENT_STATUS_LABELS; readonly filters = this.fb.nonNullable.group({ status: [''], search: [''] });
  enrollments: TrainingEnrollment[] = []; loading = true; error = '';
  get role() { return this.auth.currentUserSnapshot?.role; }
  get managerMode() { return this.role === 'BU_MANAGER'; }
  get adminMode() { return this.role === 'SUPER_ADMIN'; }
  ngOnInit(): void { this.load(); }
  load(): void { this.loading = true; this.error = ''; this.service.getEnrollments(this.filters.getRawValue()).pipe(finalize(() => this.loading = false)).subscribe({ next: data => this.enrollments = data.results, error: () => this.error = 'Impossible de charger les inscriptions.' }); }
  decide(item: TrainingEnrollment, action: 'manager_approve'|'manager_reject'|'super_admin_approve'|'super_admin_reject'): void { const comment = window.prompt('Commentaire de décision (facultatif)') ?? ''; this.service.decideEnrollment(item.id, action, comment).subscribe({ next: () => { this.snack.open('Décision enregistrée.', 'Fermer', {duration:3000}); this.load(); }, error: err => this.snack.open(err.error?.detail ?? 'Action impossible.', 'Fermer', {duration:4000}) }); }
  finalAction(item: TrainingEnrollment, action: 'cancel'|'complete'): void { this.service.enrollmentAction(item.id, action).subscribe({ next: () => this.load(), error: err => this.snack.open(err.error?.detail ?? 'Action impossible.', 'Fermer', {duration:4000}) }); }
}
