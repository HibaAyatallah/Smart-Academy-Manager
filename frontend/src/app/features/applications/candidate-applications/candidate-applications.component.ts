import { DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_TYPE_LABELS,
  Application,
  ApplicationDocument,
  ApplicationStatus,
  EDUCATION_LEVEL_LABELS,
} from '../../../core/models/application.models';
import { ApplicationApiError, ApplicationService } from '../../../core/services/application.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import {
  candidateApplicationStepLabel,
  candidateApplicationStepState,
  candidateApplicationTargetLabel,
  candidateDocument,
  candidateHistoryDate,
  candidateLatestInterview,
  toSafeExternalUrl,
} from '../shared/candidate-application.utils';

@Component({
  selector: 'app-candidate-applications',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NgClass,
    NgFor,
    NgIf,
    PageHeaderComponent,
  ],
  templateUrl: './candidate-applications.component.html',
  styleUrl: './candidate-applications.component.scss',
})
export class CandidateApplicationsComponent implements OnDestroy, OnInit {
  private readonly applicationService = inject(ApplicationService);
  private readonly snackBar = inject(MatSnackBar);

  readonly typeLabels = APPLICATION_TYPE_LABELS;
  readonly statusLabels = APPLICATION_STATUS_LABELS;
  applications: Application[] = [];
  photoUrls = new Map<number, string>();
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

  ngOnDestroy(): void {
    this.photoUrls.forEach((url) => URL.revokeObjectURL(url));
  }

  loadApplications(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.applicationService
      .getMyApplications(this.pageIndex + 1)
      .pipe(
        finalize(() => {
          this.isLoading = false;
        }),
      )
      .subscribe({
        next: (response) => {
          this.applications = response.results ?? [];
          this.total = response.count;
          this.loadPhotoPreviews();
        },
        error: (error: ApplicationApiError) => {
          this.applications = [];
          this.total = 0;
          this.clearPhotoPreviews();
          this.errorMessage = this.buildErrorMessage(error);
          this.snackBar.open(this.errorMessage, 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  onPageChange(event: PageEvent): void {
    if (event.pageIndex === this.pageIndex) {
      return;
    }
    this.pageIndex = event.pageIndex;
    this.loadApplications();
  }

  stepState(application: Application, step: 0 | 1 | 2): 'done' | 'active' | 'pending' | 'rejected' {
    return candidateApplicationStepState(application, step);
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

  studyLevelBaseLabel(application: Application): string {
    return EDUCATION_LEVEL_LABELS[application.candidate_profile.study_level];
  }

  isOtherStudyLevel(application: Application): boolean {
    return application.candidate_profile.study_level === 'OTHER';
  }

  currentStepLabel(application: Application): string {
    return candidateApplicationStepLabel(application);
  }

  acceptedTargetLabel(application: Application): string {
    return candidateApplicationTargetLabel(application);
  }

  latestInterview(application: Application) {
    return candidateLatestInterview(application);
  }

  historyDate(
    application: Application,
    statuses: readonly string[],
  ): string | null {
    return candidateHistoryDate(application, statuses);
  }

  safeExternalUrl(url: string): string {
    return toSafeExternalUrl(url);
  }

  personalPhoto(application: Application) {
    return candidateDocument(application, 'PERSONAL_PHOTO');
  }

  cvDocument(application: Application) {
    return candidateDocument(application, 'CV');
  }

  coverLetterDocument(application: Application) {
    return candidateDocument(application, 'COVER_LETTER');
  }

  photoUrl(application: Application): string | null {
    return this.photoUrls.get(application.id) ?? null;
  }

  openDocument(document: ApplicationDocument | undefined): void {
    if (!document) {
      return;
    }
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

  private loadPhotoPreviews(): void {
    this.clearPhotoPreviews();

    this.applications.forEach((application) => {
      const photo = this.personalPhoto(application);
      if (!photo) {
        return;
      }

      this.applicationService.downloadDocument(photo.download_url).subscribe({
        next: (blob) => {
          this.photoUrls.set(application.id, URL.createObjectURL(blob));
        },
      });
    });
  }

  private clearPhotoPreviews(): void {
    this.photoUrls.forEach((url) => URL.revokeObjectURL(url));
    this.photoUrls.clear();
  }

  private buildErrorMessage(error: ApplicationApiError): string {
    const status = error?.status || 0;
    return `Impossible de charger vos candidatures. Statut HTTP : ${status}.`;
  }


}
