import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { EMPTY, forkJoin, of } from 'rxjs';
import { catchError, expand, finalize, map, reduce, switchMap } from 'rxjs/operators';

import { ROLE_LABELS, UserRole } from '../../../core/models/auth.models';
import { ENROLLMENT_STATUS_LABELS, TrainingEnrollment } from '../../../core/models/training.models';
import { TrainingService } from '../../../core/services/training.service';
import { UserManagementService } from '../../../core/services/user-management.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

interface ParticipantRow extends TrainingEnrollment { user_role?: UserRole; }

@Component({
  selector: 'app-training-participants', standalone: true,
  imports: [DatePipe, NgIf, MatCardModule, MatProgressSpinnerModule, MatTableModule, EmptyStateComponent, PageHeaderComponent],
  templateUrl: './training-participants.component.html', styleUrl: './training-participants.component.scss',
})
export class TrainingParticipantsComponent implements OnInit {
  private readonly trainings = inject(TrainingService);
  private readonly users = inject(UserManagementService);
  readonly columns = ['user_name','user_email','role','training','session','requested_at','status'];
  readonly roleLabels = ROLE_LABELS;
  readonly statusLabels = ENROLLMENT_STATUS_LABELS;
  rows: ParticipantRow[] = []; loading = true; error = '';

  ngOnInit(): void { this.load(); }
  roleLabel(role?: UserRole): string { return role ? this.roleLabels[role] : '—'; }

  load(): void {
    let page = 1; this.loading = true; this.error = '';
    this.trainings.getEnrollments({page}).pipe(
      expand(response => response.next ? this.trainings.getEnrollments({page: ++page}) : EMPTY),
      map(response => response.results),
      reduce((all, current) => [...all, ...current], [] as TrainingEnrollment[]),
      switchMap(enrollments => {
        const ids = [...new Set(enrollments.map(item => item.user))];
        if (!ids.length) return of([] as ParticipantRow[]);
        return forkJoin(ids.map(id => this.users.getUser(id).pipe(catchError(() => of(null))))).pipe(
          map(profiles => {
            const roles = new Map(profiles.filter(Boolean).map(profile => [profile!.id, profile!.role]));
            return enrollments.map(item => ({...item, user_role: roles.get(item.user)}));
          }),
        );
      }),
      finalize(() => this.loading = false),
    ).subscribe({next: rows => this.rows = rows, error: () => this.error = 'Impossible de charger les personnes inscrites.'});
  }
}
