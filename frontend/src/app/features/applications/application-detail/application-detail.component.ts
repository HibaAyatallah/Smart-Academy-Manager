import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { finalize, switchMap } from 'rxjs/operators';

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_TYPE_LABELS,
  Application,
  ApplicationDocument,
  ApplicationStatus,
  EDUCATION_LEVEL_LABELS,
} from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import {
  ConfirmDialogComponent,
  ConfirmDialogData,
} from '../shared/confirm-dialog/confirm-dialog.component';
import { RejectionDialogComponent } from '../shared/rejection-dialog/rejection-dialog.component';
import {
  ScheduleInterviewDialogComponent,
  ScheduleInterviewDialogResult,
} from '../shared/schedule-interview-dialog/schedule-interview-dialog.component';

@Component({
  selector: 'app-application-detail',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NgFor,
    NgIf,
    PageHeaderComponent,
    RouterLink,
  ],
  templateUrl: './application-detail.component.html',
  styleUrl: './application-detail.component.scss',
})
export class ApplicationDetailComponent implements OnInit {
  private readonly applicationService = inject(ApplicationService);
  private readonly dialog = inject(MatDialog);
  private readonly route = inject(ActivatedRoute);
  private readonly snackBar = inject(MatSnackBar);

  readonly typeLabels = APPLICATION_TYPE_LABELS;
  readonly statusLabels = APPLICATION_STATUS_LABELS;
  application: Application | null = null;
  isLoading = true;
  isActionRunning = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    this.loadApplication();
  }

  loadApplication(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (isNaN(id) || id <= 0) {
      this.errorMessage = 'La référence de la candidature est invalide.';
      this.isLoading = false;
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    this.applicationService.getApplication(id).subscribe({
      next: (application) => {
        this.application = application;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        if (error.status === 404) {
          this.errorMessage = "Cette candidature n'existe pas ou a été supprimée.";
        } else if (error.status === 403) {
          this.errorMessage = "Accès refusé. Vous n'avez pas la permission de consulter cette candidature.";
        } else {
          this.errorMessage = "Impossible de charger la candidature. Une erreur est survenue.";
        }
        this.snackBar.open(this.errorMessage, 'Fermer', {
          duration: 4000,
        });
      },
    });
  }

  markUnderReview(): void {
    this.confirmAndRun(
      {
        title: 'Passer en revue',
        message: 'Confirmer le passage de cette candidature en cours d etude ?',
      },
      () => this.applicationService.markUnderReview(this.requireApplicationId()),
      'La candidature est maintenant en revue.',
    );
  }

  preselect(): void {
    this.confirmAndRun(
      {
        title: 'Preselectionner',
        message: 'Confirmer la preselection de ce candidat ?',
      },
      () => this.applicationService.preselect(this.requireApplicationId()),
      'Le candidat a été présélectionné.',
    );
  }

  scheduleInterview(): void {
    if (this.isActionRunning) {
      return;
    }

    const application = this.requireApplication();
    this.isActionRunning = true;
    this.dialog
      .open(ScheduleInterviewDialogComponent, {
        data: {
          candidateName: application.candidate_profile.full_name,
        },
        width: '520px',
      })
      .afterClosed()
      .subscribe((result: ScheduleInterviewDialogResult | null) => {
        if (!result) {
          this.isActionRunning = false;
          return;
        }
        this.runAction(
          () => this.applicationService.scheduleInterview(application.id, result),
          'L’entretien a été planifié.',
        );
      });
  }

  completeInterview(): void {
    this.confirmAndRun(
      {
        title: 'Entretien realise',
        message: 'Confirmer que l entretien est termine ?',
      },
      () => this.applicationService.completeInterview(this.requireApplicationId()),
      'L’entretien a été marqué comme réalisé.',
    );
  }

  accept(): void {
    this.confirmAndRun(
      {
        title: 'Accepter la candidature',
        message: 'Le role du compte sera transforme automatiquement. Confirmer ?',
        confirmLabel: 'Accepter',
      },
      () => this.applicationService.accept(this.requireApplicationId()),
      'La candidature a été acceptée.',
    );
  }

  reject(): void {
    if (this.isActionRunning) {
      return;
    }

    const application = this.requireApplication();
    this.isActionRunning = true;
    this.dialog
      .open(RejectionDialogComponent, {
        data: {
          candidateName: application.candidate_profile.full_name,
        },
        width: '520px',
      })
      .afterClosed()
      .subscribe((reason: string | null) => {
        if (!reason) {
          this.isActionRunning = false;
          return;
        }
        this.runAction(
          () => this.applicationService.reject(application.id, reason),
          'La candidature a été refusée.',
        );
      });
  }

  canMarkUnderReview(statusValue: ApplicationStatus): boolean {
    return statusValue === 'SUBMITTED';
  }

  canPreselect(statusValue: ApplicationStatus): boolean {
    return statusValue === 'SUBMITTED' || statusValue === 'UNDER_REVIEW';
  }

  canSchedule(statusValue: ApplicationStatus): boolean {
    return statusValue === 'PRESELECTED';
  }

  canCompleteInterview(statusValue: ApplicationStatus): boolean {
    return statusValue === 'INTERVIEW_SCHEDULED';
  }

  canAccept(statusValue: ApplicationStatus): boolean {
    return ['PRESELECTED', 'INTERVIEW_SCHEDULED', 'INTERVIEW_COMPLETED'].includes(statusValue);
  }

  canReject(statusValue: ApplicationStatus): boolean {
    return !['ACCEPTED', 'REJECTED', 'CANCELLED'].includes(statusValue);
  }

  typeLabel(value: Application['application_type']): string {
    return APPLICATION_TYPE_LABELS[value];
  }

  statusLabel(value: ApplicationStatus): string {
    return APPLICATION_STATUS_LABELS[value];
  }

  studyLevelLabel(application: Application): string {
    if (application.candidate_profile.study_level === 'OTHER') {
      return application.candidate_profile.study_level_other || 'Autre';
    }
    return EDUCATION_LEVEL_LABELS[application.candidate_profile.study_level];
  }

  openDocument(document: ApplicationDocument): void {
    this.applicationService.downloadDocument(document.download_url).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noopener');
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      },
      error: () => {
        this.snackBar.open('Impossible d ouvrir le document.', 'Fermer', {
          duration: 4000,
        });
      },
    });
  }

  documentTypeLabel(document: ApplicationDocument): string {
    if (document.document_type === 'COVER_LETTER') {
      return 'Lettre de motivation';
    }
    if (document.document_type === 'PERSONAL_PHOTO') {
      return 'Photo personnelle';
    }
    return document.document_type;
  }

  private confirmAndRun(
    data: ConfirmDialogData,
    action: () => Observable<Application>,
    successMessage: string,
  ): void {
    if (this.isActionRunning) {
      return;
    }

    this.isActionRunning = true;
    this.dialog
      .open(ConfirmDialogComponent, {
        data,
        width: '460px',
      })
      .afterClosed()
      .subscribe((confirmed: boolean) => {
        if (!confirmed) {
          this.isActionRunning = false;
          return;
        }
        this.runAction(action, successMessage);
      });
  }

  private runAction(action: () => Observable<Application>, successMessage: string): void {
    action()
      .pipe(
        switchMap(() => this.applicationService.getApplication(this.requireApplicationId())),
        finalize(() => {
          this.isActionRunning = false;
        })
      )
      .subscribe({
        next: (application) => this.handleActionSuccess(application, successMessage),
        error: (error: unknown) => this.handleActionError(error),
      });
  }

  private handleActionSuccess(application: Application, message: string): void {
    this.application = application;
    this.isActionRunning = false;
    this.snackBar.open(message, 'Fermer', { duration: 3500 });
  }

  private handleActionError(error: unknown): void {
    this.isActionRunning = false;
    this.snackBar.open(this.actionErrorMessage(error), 'Fermer', { duration: 5000 });
  }

  private actionErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse && error.error && typeof error.error === 'object') {
      const details = error.error as Record<string, unknown>;
      const message = details['detail'] ?? details['non_field_errors'];
      if (Array.isArray(message)) {
        return message.map(String).join(' ');
      }
      if (typeof message === 'string') {
        return message;
      }
    }
    return 'L’action n’a pas pu être effectuée. Réessayez ou vérifiez le statut de la candidature.';
  }

  private requireApplication(): Application {
    if (!this.application) {
      throw new Error('Application is not loaded.');
    }
    return this.application;
  }

  private requireApplicationId(): number {
    return this.requireApplication().id;
  }
}
