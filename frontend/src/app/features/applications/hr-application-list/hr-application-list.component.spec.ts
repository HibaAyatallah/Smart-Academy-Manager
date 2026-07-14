import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { Application } from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';
import { HrApplicationListComponent } from './hr-application-list.component';

describe('HrApplicationListComponent', () => {
  let fixture: ComponentFixture<HrApplicationListComponent>;
  let component: HrApplicationListComponent;
  let applicationService: jasmine.SpyObj<ApplicationService>;

  beforeEach(async () => {
    applicationService = jasmine.createSpyObj<ApplicationService>('ApplicationService', [
      'listApplications',
    ]);

    await TestBed.configureTestingModule({
      imports: [HrApplicationListComponent],
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

  it('stops loading when the paginated list is received', () => {
    const application = {
      id: 1,
      candidate_profile: {
        full_name: 'Candidate One',
        email: 'candidate@example.com',
      },
      application_type: 'PFA_INTERNSHIP',
      status: 'SUBMITTED',
      submitted_at: '2026-07-10T10:00:00Z',
    } as Application;

    applicationService.listApplications.and.returnValue(
      of({
        count: 1,
        next: null,
        previous: null,
        results: [application],
      }),
    );

    fixture = TestBed.createComponent(HrApplicationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isLoading).toBeFalse();
    expect(component.total).toBe(1);
    expect(component.applications).toEqual([application]);
  });

  it('shows the expected empty state when no application is returned', () => {
    applicationService.listApplications.and.returnValue(
      of({
        count: 0,
        next: null,
        previous: null,
        results: [],
      }),
    );

    fixture = TestBed.createComponent(HrApplicationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const emptyState = fixture.nativeElement.querySelector('.empty-state') as HTMLElement | null;
    expect(component.isLoading).toBeFalse();
    expect(emptyState?.textContent?.trim()).toBe('Aucune candidature trouvée.');
  });

  it('stops loading and shows an error message when the API fails', () => {
    applicationService.listApplications.and.returnValue(
      throwError(() => ({
        status: 403,
        message: 'Forbidden',
        raw: null,
      })),
    );

    fixture = TestBed.createComponent(HrApplicationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isLoading).toBeFalse();
    expect(component.errorMessage).toBe('Impossible de charger les candidatures. Statut HTTP : 403.');
  });

  it('calls loadApplications immediately on init without waiting for a profile Observable', () => {
    // The guard has already validated the session before activating this
    // component, so the component must NOT delay the API call behind an
    // ensureProfile() subscription.
    applicationService.listApplications.and.returnValue(
      of({ count: 0, next: null, previous: null, results: [] }),
    );

    fixture = TestBed.createComponent(HrApplicationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    // listApplications must have been called in the same synchronous tick
    // as ngOnInit (no deferred profile Observable in between).
    expect(applicationService.listApplications).toHaveBeenCalledTimes(1);
    expect(component.isLoading).toBeFalse();
  });
});
