import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { Application } from '../../core/models/application.models';
import { UserProfile } from '../../core/models/auth.models';
import { ApplicationService } from '../../core/services/application.service';
import { AuthService } from '../../core/services/auth.service';
import { DashboardComponent } from './dashboard.component';

const candidateUser: UserProfile = {
  id: 1,
  email: 'candidate@example.com',
  first_name: 'Jane',
  last_name: 'Candidate',
  full_name: 'Jane Candidate',
  phone_number: '+212600000000',
  role: 'CANDIDATE',
};

const candidateApplication: Application = {
  id: 12,
  candidate_profile: {
    id: 3,
    email: 'candidate@example.com',
    first_name: 'Jane',
    last_name: 'Candidate',
    full_name: 'Jane Candidate',
    role: 'CANDIDATE',
    is_active: true,
    phone_number: '+212600000000',
    current_school: 'Smart University',
    study_level: 'MASTER',
    study_level_label: 'Master',
    study_level_other: '',
    study_field: 'Developpement logiciel',
    linkedin_url: 'linkedin.com/in/jane',
    portfolio_url: '',
    address: '',
  },
  application_type: 'PFE_INTERNSHIP',
  application_type_label: 'Stage PFE',
  status: 'INTERVIEW_SCHEDULED',
  status_label: 'Entretien planifie',
  motivation_message: 'Motivation',
  rejection_reason: '',
  submitted_at: '2026-07-10T10:00:00Z',
  updated_at: '2026-07-10T11:00:00Z',
  accepted_at: null,
  rejected_at: null,
  cancelled_at: null,
  retention_until: null,
  documents: [
    {
      id: 1,
      application: 12,
      document_type: 'CV',
      download_url: '/api/application-documents/1/download/',
      original_name: 'cv.pdf',
      content_type: 'application/pdf',
      size: 1000,
      uploaded_by_email: 'candidate@example.com',
      uploaded_at: '2026-07-10T10:00:00Z',
    },
    {
      id: 2,
      application: 12,
      document_type: 'COVER_LETTER',
      download_url: '/api/application-documents/2/download/',
      original_name: 'lettre.pdf',
      content_type: 'application/pdf',
      size: 1000,
      uploaded_by_email: 'candidate@example.com',
      uploaded_at: '2026-07-10T10:00:00Z',
    },
  ],
  interviews: [
    {
      id: 1,
      application: 12,
      scheduled_at: '2026-07-12T09:00:00Z',
      location: 'Salle RH',
      meeting_link: '',
      interviewer: null,
      interviewer_email: 'hr@example.com',
      notes: '',
      result: '',
      created_by_email: 'hr@example.com',
      created_at: '2026-07-10T11:00:00Z',
      updated_at: '2026-07-10T11:00:00Z',
    },
  ],
  status_history: [
    {
      id: 1,
      from_status: 'PRESELECTED',
      to_status: 'INTERVIEW_SCHEDULED',
      changed_by_email: 'hr@example.com',
      comment: '',
      created_at: '2026-07-10T11:00:00Z',
    },
  ],
};

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let applicationService: jasmine.SpyObj<ApplicationService>;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    applicationService = jasmine.createSpyObj<ApplicationService>('ApplicationService', [
      'downloadDocument',
      'getMyApplications',
    ]);
    authService = jasmine.createSpyObj<AuthService>(
      'AuthService',
      ['ensureProfile', 'logout'],
      {
        currentUser$: of(candidateUser),
        // Provide the snapshot so ngOnInit() can resolve synchronously.
        currentUserSnapshot: candidateUser,
      },
    );
    authService.ensureProfile.and.returnValue(of(candidateUser));

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideNoopAnimations(),
        {
          provide: ActivatedRoute,
          useValue: {
            data: of({ title: 'Dashboard candidat' }),
          },
        },
        {
          provide: AuthService,
          useValue: authService,
        },
        {
          provide: ApplicationService,
          useValue: applicationService,
        },
        {
          provide: MatSnackBar,
          useValue: {
            open: jasmine.createSpy(),
          },
        },
      ],
    }).compileComponents();
  });

  it('loads candidate applications on the candidate dashboard', () => {
    applicationService.getMyApplications.and.returnValue(
      of({
        count: 1,
        next: null,
        previous: null,
        results: [candidateApplication],
      }),
    );

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(applicationService.getMyApplications).toHaveBeenCalled();
    expect(component.candidateApplicationsLoading).toBeFalse();
    expect(component.candidateApplications.length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('candidate@example.com');
    expect(fixture.nativeElement.textContent).toContain('Stage PFE');
  });

  it('stops loading and shows an error when candidate applications fail', () => {
    applicationService.getMyApplications.and.returnValue(
      throwError(() => new Error('API unavailable')),
    );

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.candidateApplicationsLoading).toBeFalse();
    expect(component.candidateApplicationsError).toBe('Impossible de charger vos candidatures.');
  });

  it('loads applications synchronously from the snapshot without an Observable round-trip', () => {
    // The roleGuard put the profile in currentUserSnapshot before activating
    // the component. ngOnInit() must resolve the role synchronously and call
    // loadCandidateApplications() without subscribing to currentUser$.
    applicationService.getMyApplications.and.returnValue(
      of({ count: 0, next: null, previous: null, results: [] }),
    );

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(applicationService.getMyApplications).toHaveBeenCalledTimes(1);
    expect(component.candidateApplicationsLoading).toBeFalse();
  });

  it('falls back to currentUser$ when currentUserSnapshot is null', () => {
    // Override the snapshot to simulate the rare edge case where the guard
    // has not yet populated the cache (e.g. a custom route bypass).
    Object.defineProperty(authService, 'currentUserSnapshot', { get: () => null });
    authService.ensureProfile.and.returnValue(of(candidateUser));

    applicationService.getMyApplications.and.returnValue(
      of({ count: 0, next: null, previous: null, results: [] }),
    );

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(applicationService.getMyApplications).toHaveBeenCalledTimes(1);
    expect(component.candidateApplicationsLoading).toBeFalse();
  });
});
