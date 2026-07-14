import { AsyncPipe, DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { filter, finalize, map, take } from 'rxjs/operators';

import { ROLE_LABELS } from '../../core/models/auth.models';
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_TYPE_LABELS,
  Application,
  ApplicationDocument,
  ApplicationStatus,
  EDUCATION_LEVEL_LABELS,
} from '../../core/models/application.models';
import { ApplicationService } from '../../core/services/application.service';
import { AuthService } from '../../core/services/auth.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import {
  candidateApplicationStepLabel,
  candidateApplicationStepState,
  candidateApplicationTargetLabel,
  candidateDocument,
  candidateHistoryDate,
  candidateLatestInterview,
  toSafeExternalUrl,
} from '../applications/shared/candidate-application.utils';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    AsyncPipe,
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
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnDestroy, OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly applicationService = inject(ApplicationService);
  private readonly snackBar = inject(MatSnackBar);

  readonly roleLabels = ROLE_LABELS;
  readonly typeLabels = APPLICATION_TYPE_LABELS;
  readonly statusLabels = APPLICATION_STATUS_LABELS;
  readonly user$ = this.authService.currentUser$;
  readonly title$ = this.route.data.pipe(map((data) => data['title'] as string));
  candidateApplications: Application[] = [];
  candidatePhotoUrls = new Map<number, string>();
  candidateApplicationsTotal = 0;
  candidatePageIndex = 0;
  readonly candidatePageSize = 20;
  candidateApplicationsLoading = false;
  candidateApplicationsError = '';

  ngOnInit(): void {
    // The roleGuard already guarantees the profile is available before this
    // component is activated. Use the synchronous snapshot to avoid an
    // unnecessary asynchronous round-trip that could delay the first render.
    const user = this.authService.currentUserSnapshot;
    if (user) {
      if (user.role === 'CANDIDATE') {
        this.loadCandidateApplications();
      }
      return;
    }
    // Fallback: profile not yet in cache (should not happen in practice
    // thanks to the guard, but keeps the component self-contained).
    this.authService.currentUser$.pipe(
      filter((u): u is NonNullable<typeof u> => u !== null),
      take(1),
    ).subscribe((u) => {
      if (u.role === 'CANDIDATE') {
        this.loadCandidateApplications();
      }
    });
  }

  ngOnDestroy(): void {
    this.candidatePhotoUrls.forEach((url) => URL.revokeObjectURL(url));
  }

  logout(): void {
    this.authService.logout();
  }

  loadCandidateApplications(): void {
    this.candidateApplicationsLoading = true;
    this.candidateApplicationsError = '';
    this.applicationService
      .getMyApplications(this.candidatePageIndex + 1)
      .pipe(
        finalize(() => {
          this.candidateApplicationsLoading = false;
        }),
      )
      .subscribe({
        next: (response) => {
          this.candidateApplications = response.results ?? [];
          this.candidateApplicationsTotal = response.count;
          this.loadCandidatePhotoPreviews();
        },
        error: () => {
          this.candidateApplications = [];
          this.candidateApplicationsTotal = 0;
          this.candidateApplicationsError = 'Impossible de charger vos candidatures.';
          this.snackBar.open('Impossible de charger vos candidatures.', 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  onCandidatePageChange(event: PageEvent): void {
    if (event.pageIndex === this.candidatePageIndex) {
      return;
    }
    this.candidatePageIndex = event.pageIndex;
    this.loadCandidateApplications();
  }

  typeLabel(value: Application['application_type']): string {
    return APPLICATION_TYPE_LABELS[value];
  }

  statusLabel(value: ApplicationStatus): string {
    return APPLICATION_STATUS_LABELS[value];
  }

  studyLevelBaseLabel(application: Application): string {
    return EDUCATION_LEVEL_LABELS[application.candidate_profile.study_level];
  }

  isOtherStudyLevel(application: Application): boolean {
    return application.candidate_profile.study_level === 'OTHER';
  }

  acceptedTargetLabel(application: Application): string {
    return candidateApplicationTargetLabel(application);
  }

  stepState(application: Application, step: 0 | 1 | 2): 'done' | 'active' | 'pending' | 'rejected' {
    return candidateApplicationStepState(application, step);
  }

  currentStepLabel(application: Application): string {
    return candidateApplicationStepLabel(application);
  }

  historyDate(application: Application, statuses: readonly string[]): string | null {
    return candidateHistoryDate(application, statuses);
  }

  latestInterview(application: Application) {
    return candidateLatestInterview(application);
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
    return this.candidatePhotoUrls.get(application.id) ?? null;
  }

  safeExternalUrl(url: string): string {
    return toSafeExternalUrl(url);
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

  private loadCandidatePhotoPreviews(): void {
    this.candidatePhotoUrls.forEach((url) => URL.revokeObjectURL(url));
    this.candidatePhotoUrls.clear();

    this.candidateApplications.forEach((application) => {
      const photo = this.personalPhoto(application);
      if (!photo) {
        return;
      }

      this.applicationService.downloadDocument(photo.download_url).subscribe({
        next: (blob) => {
          this.candidatePhotoUrls.set(application.id, URL.createObjectURL(blob));
        },
      });
    });
  }

}
