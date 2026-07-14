import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PageEvent } from '@angular/material/paginator';
import { of, throwError } from 'rxjs';

import { Application } from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';
import { CandidateApplicationsComponent } from './candidate-applications.component';

describe('CandidateApplicationsComponent', () => {
  let fixture: ComponentFixture<CandidateApplicationsComponent>;
  let component: CandidateApplicationsComponent;
  let applicationService: jasmine.SpyObj<ApplicationService>;

  beforeEach(async () => {
    applicationService = jasmine.createSpyObj<ApplicationService>('ApplicationService', [
      'downloadDocument',
      'getMyApplications',
    ]);

    await TestBed.configureTestingModule({
      imports: [CandidateApplicationsComponent],
      providers: [
        provideNoopAnimations(),
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

  it('stops loading and displays a paginated personal list response', () => {
    const application = {
      id: 1,
      candidate_profile: {
        id: 1,
        email: 'candidate@example.com',
        first_name: 'Candidate',
        last_name: 'One',
        full_name: 'Candidate One',
        role: 'CANDIDATE',
        is_active: true,
        phone_number: '+212600000000',
        current_school: 'Smart University',
        study_level: 'MASTER',
        study_level_label: 'Master',
        study_level_other: '',
        study_field: 'Developpement logiciel',
        linkedin_url: '',
        portfolio_url: '',
        address: '',
      },
      application_type: 'PFA_INTERNSHIP',
      application_type_label: 'Stage PFA',
      status: 'SUBMITTED',
      status_label: 'T0 - Candidature deposee',
      motivation_message: '',
      rejection_reason: '',
      submitted_at: '2026-07-10T10:00:00Z',
      updated_at: '2026-07-10T10:00:00Z',
      accepted_at: null,
      rejected_at: null,
      cancelled_at: null,
      retention_until: null,
      documents: [],
      interviews: [],
      status_history: [],
    } as Application;

    applicationService.getMyApplications.and.returnValue(
      of({
        count: 1,
        next: null,
        previous: null,
        results: [application],
      }),
    );

    fixture = TestBed.createComponent(CandidateApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isLoading).toBeFalse();
    expect(component.applications).toEqual([application]);
    expect(component.total).toBe(1);
  });

  it('shows the expected empty state when the candidate has no application', () => {
    applicationService.getMyApplications.and.returnValue(
      of({
        count: 0,
        next: null,
        previous: null,
        results: [],
      }),
    );

    fixture = TestBed.createComponent(CandidateApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const emptyState = fixture.nativeElement.querySelector('.empty-state') as HTMLElement | null;
    expect(component.isLoading).toBeFalse();
    expect(emptyState?.textContent?.trim()).toBe('Aucune candidature trouvée.');
  });

  it('requests the selected DRF page for the candidate list', () => {
    applicationService.getMyApplications.and.returnValue(
      of({
        count: 21,
        next: 'http://127.0.0.1:8000/api/applications/mine/?page=2',
        previous: null,
        results: [],
      }),
    );
    fixture = TestBed.createComponent(CandidateApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    applicationService.getMyApplications.calls.reset();

    component.onPageChange({
      length: 21,
      pageIndex: 1,
      pageSize: 20,
      previousPageIndex: 0,
    } satisfies PageEvent);

    expect(component.pageIndex).toBe(1);
    expect(applicationService.getMyApplications).toHaveBeenCalledWith(2);
  });

  it('stops loading and exposes an error message when the API fails', () => {
    applicationService.getMyApplications.and.returnValue(
      throwError(() => ({
        status: 500,
        message: 'API unavailable',
        raw: null,
      })),
    );

    fixture = TestBed.createComponent(CandidateApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isLoading).toBeFalse();
    expect(component.errorMessage).toBe('Impossible de charger vos candidatures. Statut HTTP : 500.');
  });

  it('calls getMyApplications immediately on init without waiting for a profile Observable', () => {
    // The roleGuard already validated CANDIDATE role before activating this
    // component. No ensureProfile() Observable should stand between ngOnInit
    // and the API call.
    applicationService.getMyApplications.and.returnValue(
      of({ count: 0, next: null, previous: null, results: [] }),
    );

    fixture = TestBed.createComponent(CandidateApplicationsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    // getMyApplications must be called in the same synchronous tick as ngOnInit.
    expect(applicationService.getMyApplications).toHaveBeenCalledTimes(1);
    expect(component.isLoading).toBeFalse();
  });
});
