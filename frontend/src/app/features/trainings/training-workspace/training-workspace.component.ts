import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';
import { SESSION_STATUS_LABELS, TRAINING_STATUS_LABELS, Training, TrainingSession } from '../../../core/models/training.models';
import { AuthService } from '../../../core/services/auth.service';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-training-workspace', standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatCardModule, MatChipsModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, MatSnackBarModule, PageHeaderComponent],
  templateUrl: './training-workspace.component.html', styleUrl: './training-workspace.component.scss',
})
export class TrainingWorkspaceComponent implements OnInit {
  private readonly service = inject(TrainingService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly snack = inject(MatSnackBar);
  readonly trainingLabels = TRAINING_STATUS_LABELS;
  readonly sessionLabels = SESSION_STATUS_LABELS;
  trainings: Training[] = [];
  selected: Training | null = null;
  loading = true;
  saving = false;
  error = '';
  showTrainingForm = false;
  showSessionForm = false;
  editingTrainingId: number | null = null;
  editingSessionId: number | null = null;

  readonly filters = this.fb.nonNullable.group({ search: [''], status: [''] });
  readonly trainingForm = this.fb.nonNullable.group({
    title: ['', Validators.required], description: ['', Validators.required], training_type: ['INTERNAL', Validators.required],
    category: ['', Validators.required], objectives: ['', Validators.required], prerequisites: [''], duration: [1, [Validators.required, Validators.min(1)]],
    delivery_mode: ['ON_SITE', Validators.required], level: ['', Validators.required], trainer: [null as number | null], business_unit: [null as number | null],
    external_client: [null as number | null], project_name: [''], associated_link: [''], moodle_course_id: [''], moodle_link: [''],
  });
  readonly sessionForm = this.fb.nonNullable.group({
    start_date: ['', Validators.required], end_date: ['', Validators.required], start_time: ['', Validators.required], end_time: ['', Validators.required],
    location: [''], online_link: [''], trainer: [null as number | null], maximum_participants: [1, [Validators.required, Validators.min(1)]], external_client: [null as number | null],
  });

  get role() { return this.auth.currentUserSnapshot?.role; }
  get canManage() { return this.role === 'SUPER_ADMIN' || this.role === 'HR'; }
  get canRequest() { return ['EMPLOYEE', 'INTERN', 'BU_MANAGER', 'TRAINER_TUTOR'].includes(this.role ?? ''); }

  ngOnInit(): void { this.load(); }
  load(): void {
    this.loading = true; this.error = '';
    this.service.getTrainings(this.filters.getRawValue()).pipe(finalize(() => this.loading = false)).subscribe({
      next: result => { this.trainings = result.results; if (this.selected) this.selected = this.trainings.find(item => item.id === this.selected?.id) ?? null; },
      error: () => this.error = 'Impossible de charger les formations.',
    });
  }
  select(training: Training): void { this.selected = training; this.showTrainingForm = false; this.showSessionForm = false; }
  newTraining(): void { this.editingTrainingId = null; this.trainingForm.reset({ training_type: 'INTERNAL', delivery_mode: 'ON_SITE', duration: 1 }); this.showTrainingForm = true; }
  editTraining(training: Training): void { this.editingTrainingId = training.id; this.trainingForm.patchValue(training); this.showTrainingForm = true; }
  saveTraining(): void {
    if (this.trainingForm.invalid) { this.trainingForm.markAllAsTouched(); return; }
    this.saving = true; const data = this.trainingForm.getRawValue();
    const request = this.editingTrainingId ? this.service.updateTraining(this.editingTrainingId, data) : this.service.createTraining(data);
    request.pipe(finalize(() => this.saving = false)).subscribe({ next: training => { this.showTrainingForm = false; this.selected = training; this.notice('Formation enregistrée.'); this.load(); }, error: err => this.notice(err.error?.detail ?? 'Enregistrement impossible.') });
  }
  trainingAction(training: Training, action: 'publish' | 'archive'): void { this.service.trainingAction(training.id, action).subscribe({ next: () => { this.notice('Statut mis à jour.'); this.load(); }, error: () => this.notice('Mise à jour impossible.') }); }
  newSession(): void { this.editingSessionId = null; this.sessionForm.reset({ maximum_participants: 1 }); this.showSessionForm = true; }
  editSession(session: TrainingSession): void { this.editingSessionId = session.id; this.sessionForm.patchValue(session); this.showSessionForm = true; }
  saveSession(): void {
    if (!this.selected || this.sessionForm.invalid) { this.sessionForm.markAllAsTouched(); return; }
    this.saving = true; const data = { ...this.sessionForm.getRawValue(), training: this.selected.id };
    const request = this.editingSessionId ? this.service.updateSession(this.editingSessionId, data) : this.service.createSession(data);
    request.pipe(finalize(() => this.saving = false)).subscribe({ next: () => { this.showSessionForm = false; this.notice('Session enregistrée.'); this.reloadSelected(); }, error: err => this.notice(err.error?.detail ?? 'Session invalide.') });
  }
  sessionAction(session: TrainingSession, action: 'open_registration' | 'close_registration' | 'cancel' | 'complete'): void { this.service.sessionAction(session.id, action).subscribe({ next: () => { this.notice('Session mise à jour.'); this.reloadSelected(); }, error: () => this.notice('Action impossible.') }); }
  enroll(session: TrainingSession): void { if (!this.selected) return; this.service.requestEnrollment(this.selected.id, session.id).subscribe({ next: () => this.notice('Demande d\'inscription envoyée.'), error: err => this.notice(err.error?.non_field_errors?.[0] ?? err.error?.detail ?? 'Inscription impossible.') }); }
  private reloadSelected(): void { if (!this.selected) return; this.service.getTraining(this.selected.id).subscribe(training => { this.selected = training; this.load(); }); }
  private notice(message: string): void { this.snack.open(message, 'Fermer', { duration: 4000 }); }
}
