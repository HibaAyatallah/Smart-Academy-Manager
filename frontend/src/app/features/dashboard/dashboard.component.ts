import { AsyncPipe, DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, ViewChildren, QueryList, ElementRef, AfterViewInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Observable } from 'rxjs';
import { finalize, map, shareReplay, take } from 'rxjs/operators';

import { ROLE_LABELS } from '../../core/models/auth.models';
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_TYPE_LABELS,
  Application,
  ApplicationDocument,
  ApplicationStatus,
  EDUCATION_LEVEL_LABELS,
} from '../../core/models/application.models';
import { ReportData, HRDashboardData } from '../../core/models/report.models';
import { ApplicationService } from '../../core/services/application.service';
import { AuthService } from '../../core/services/auth.service';
import { ReportService } from '../../core/services/report.service';
import { InternshipService } from '../../core/services/internship.service';
import { InternProfile, INTERNSHIP_STATUS_LABELS } from '../../core/models/internship.models';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
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
    EmptyStateComponent,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule,
    MatTooltipModule,
    NgClass,
    NgFor,
    NgIf,
    PageHeaderComponent,
    RouterLink,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnDestroy, OnInit, AfterViewInit {
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly applicationService = inject(ApplicationService);
  private readonly reportService = inject(ReportService);
  private readonly internshipService = inject(InternshipService);
  private readonly snackBar = inject(MatSnackBar);

  readonly roleLabels = ROLE_LABELS;
  readonly typeLabels = APPLICATION_TYPE_LABELS;
  readonly statusLabels = APPLICATION_STATUS_LABELS;
  readonly user$ = this.authService.ensureProfile().pipe(
    shareReplay({ bufferSize: 1, refCount: true }),
  );
  readonly title$ = this.route.data.pipe(map((data) => data['title'] as string));
  
  // Super Admin Data
  reportData: ReportData | null = null;
  reportLoading = false;
  reportError = '';
  readonly periods = [
    { value: '7d', label: '7 jours' },
    { value: '30d', label: '30 jours' },
    { value: '3m', label: '3 mois' },
    { value: 'year', label: 'Cette année' },
  ] as const;
  selectedPeriod: '7d' | '30d' | '3m' | 'year' = '30d';
  
  // HR Data
  hrReportData: HRDashboardData | null = null;
  hrReportLoading = false;
  hrReportError = '';
  
  // Candidate Data
  candidateApplications: Application[] = [];
  candidatePhotoUrls = new Map<number, string>();
  candidateApplicationsTotal = 0;
  candidatePageIndex = 0;
  readonly candidatePageSize = 20;
  candidateApplicationsLoading = false;
  candidateApplicationsError = '';
  internProfile: InternProfile | null = null;
  internLoading = false;
  internError = '';
  readonly internshipStatuses = INTERNSHIP_STATUS_LABELS;

  @ViewChildren('chartCanvas') chartCanvases!: QueryList<ElementRef<HTMLCanvasElement>>;
  private chartInstances: any[] = [];

  ngOnInit(): void {
    const user = this.authService.currentUserSnapshot;
    if (user) {
      this.loadDashboardData(user.role);
      return;
    }
    this.user$.pipe(take(1)).subscribe((u) => {
      this.loadDashboardData(u.role);
    });
  }

  ngAfterViewInit(): void {
    this.chartCanvases.changes.subscribe(() => {
      this.initCharts();
    });
  }

  private initCharts(): void {
    this.chartInstances.forEach(c => c.destroy());
    this.chartInstances = [];
    
    if (!this.reportData || this.chartCanvases.length === 0) return;
    
    const canvases = this.chartCanvases.toArray();
    
    const statusCanvas = canvases.find(c => c.nativeElement.id === 'statusChart');
    if (statusCanvas && this.reportData.series['recruitment']) {
      const data = this.reportData.series['recruitment'];
      this.chartInstances.push(new (window as any).Chart(statusCanvas.nativeElement, {
        type: 'doughnut',
        data: {
          labels: data.map(d => this.statusLabels[d.label as ApplicationStatus] || d.label),
          datasets: [{ data: data.map(d => d.value), backgroundColor: ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false }, plugins: { legend: { position: 'bottom' }, tooltip: { enabled: true } } }
      }));
    }
    
    const monthlyCanvas = canvases.find(c => c.nativeElement.id === 'monthlyChart');
    if (monthlyCanvas && this.reportData.series['monthly_applications']) {
      const data = this.reportData.series['monthly_applications'];
      this.chartInstances.push(new (window as any).Chart(monthlyCanvas.nativeElement, {
        type: 'line',
        data: {
          labels: data.map(d => d.label),
          datasets: [{ label: 'Candidatures', data: data.map(d => d.value), borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.4 }]
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { display: false }, tooltip: { enabled: true } } }
      }));
    }
    
    const workforceCanvas = canvases.find(c => c.nativeElement.id === 'workforceChart');
    if (workforceCanvas && this.reportData.series['workforce_by_bu']) {
      const raw = this.reportData.series['workforce_by_bu'];
      this.chartInstances.push(new (window as any).Chart(workforceCanvas.nativeElement, {
        type: 'bar',
        data: {
          labels: raw.map(d => d.business_unit),
          datasets: [
            { label: 'Stagiaires', data: raw.map(d => d.interns), backgroundColor: '#3b82f6' },
            { label: 'Collaborateurs', data: raw.map(d => d.collaborators), backgroundColor: '#10b981' }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { tooltip: { enabled: true } } }
      }));
    }

    const internshipCanvas = canvases.find(c => c.nativeElement.id === 'internshipChart');
    const internshipData = this.reportData.series.monthly_internships ?? [];
    if (internshipCanvas && internshipData.length) {
      this.chartInstances.push(new (window as any).Chart(internshipCanvas.nativeElement, {
        type: 'line',
        data: {
          labels: internshipData.map(item => item.label),
          datasets: [
            { label: 'Stages à venir', data: internshipData.map(item => item.upcoming), borderColor: '#8b5cf6', tension: 0.35 },
            { label: 'Stagiaires actifs', data: internshipData.map(item => item.active), borderColor: '#10b981', tension: 0.35 },
            { label: 'Stages terminés', data: internshipData.map(item => item.completed), borderColor: '#64748b', tension: 0.35 },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { tooltip: { enabled: true } } },
      }));
    }
  }

  private loadDashboardData(role: string): void {
    if (role === 'CANDIDATE') {
      this.loadCandidateApplications();
    } else if (role === 'INTERN') {
      this.loadInternDashboard();
    } else if (role === 'SUPER_ADMIN') {
      this.loadSuperAdminDashboard();
    } else if (role === 'HR') {
      this.loadHrDashboard();
    }
  }

  private loadInternDashboard(): void {
    this.internLoading = true;
    this.internshipService.getInterns().pipe(finalize(() => this.internLoading = false)).subscribe({
      next: response => this.internProfile = response.results[0] ?? null,
      error: () => this.internError = 'Impossible de charger votre stage.',
    });
  }

  daysRemaining(intern: InternProfile): number {
    if (!intern.internship_end) return 0;
    const end = new Date(`${intern.internship_end}T00:00:00`);
    const today = new Date(); today.setHours(0, 0, 0, 0);
    return Math.max(0, Math.ceil((end.getTime() - today.getTime()) / 86400000));
  }

  documentProgress(intern: InternProfile): {done:number;total:number} {
    return {
      total: intern.document_requirements.length,
      done: intern.document_requirements.filter(item => item.latest_submission?.status === 'VALIDATED').length,
    };
  }

  private loadSuperAdminDashboard(): void {
    this.reportLoading = true;
    this.reportError = '';
    this.reportService.summary(this.periodFilters()).pipe(
      finalize(() => this.reportLoading = false)
    ).subscribe({
      next: (data) => {
        this.reportData = data;
        // In case views are already initialized
        setTimeout(() => this.initCharts());
      },
      error: () => this.reportError = 'Impossible de charger le tableau de bord Administrateur.'
    });
  }

  selectPeriod(period: '7d' | '30d' | '3m' | 'year'): void {
    if (period === this.selectedPeriod) return;
    this.selectedPeriod = period;
    this.loadSuperAdminDashboard();
  }

  private periodFilters(): { date_from: string; date_to: string } {
    const today = new Date();
    const from = new Date(today);
    if (this.selectedPeriod === '7d') from.setDate(from.getDate() - 6);
    if (this.selectedPeriod === '30d') from.setDate(from.getDate() - 29);
    if (this.selectedPeriod === '3m') from.setMonth(from.getMonth() - 3);
    if (this.selectedPeriod === 'year') from.setMonth(0, 1);
    const isoDate = (value: Date) => value.toISOString().slice(0, 10);
    return { date_from: isoDate(from), date_to: isoDate(today) };
  }

  private loadHrDashboard(): void {
    this.hrReportLoading = true;
    this.hrReportError = '';
    this.reportService.hrDashboard().pipe(
      finalize(() => this.hrReportLoading = false)
    ).subscribe({
      next: (data) => this.hrReportData = data,
      error: () => this.hrReportError = 'Impossible de charger le tableau de bord RH.'
    });
  }

  ngOnDestroy(): void {
    this.candidatePhotoUrls.forEach((url) => URL.revokeObjectURL(url));
    this.chartInstances.forEach(c => c.destroy());
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

  getStatusClass(status: ApplicationStatus | string | null | undefined): string {
    if (!status) return 'status-archived';
    return 'status-' + status.toLowerCase();
  }

  getStatusLabel(status: ApplicationStatus | string | null | undefined): string {
    if (!status) return '';
    return this.statusLabels[status as ApplicationStatus] || status;
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
