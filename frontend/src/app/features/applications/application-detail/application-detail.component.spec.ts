import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { Application } from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';
import { ApplicationDetailComponent } from './application-detail.component';

const submittedApplication: Application = {
  id: 7,
  candidate_profile: {
    id: 1,
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
    study_field: 'Développement logiciel',
    linkedin_url: '',
    portfolio_url: '',
    address: '',
  },
  application_type: 'PFA_INTERNSHIP',
  application_type_label: 'Stage PFA',
  status: 'SUBMITTED',
  status_label: 'Candidature déposée',
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
};

describe('ApplicationDetailComponent', () => {
  let fixture: ComponentFixture<ApplicationDetailComponent>;
  let component: ApplicationDetailComponent;
  let applicationService: jasmine.SpyObj<ApplicationService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let dialog: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    applicationService = jasmine.createSpyObj<ApplicationService>('ApplicationService', [
      'getApplication',
      'markUnderReview',
    ]);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    applicationService.getApplication.and.returnValue(of(submittedApplication));

    TestBed.configureTestingModule({
      imports: [ApplicationDetailComponent],
      providers: [
        provideNoopAnimations(),
        { provide: ApplicationService, useValue: applicationService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: MatDialog, useValue: dialog },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '7' }) } },
        },
      ],
    });
    TestBed.overrideComponent(ApplicationDetailComponent, {
      remove: { imports: [MatDialogModule, MatSnackBarModule] },
    });
    await TestBed.compileComponents();

    fixture = TestBed.createComponent(ApplicationDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('locks actions, prevents a double click, then reloads the updated application', () => {
    const transition$ = new Subject<Application>();
    const underReviewApplication = { ...submittedApplication, status: 'UNDER_REVIEW' as const };
    applicationService.markUnderReview.and.returnValue(transition$.asObservable());
    applicationService.getApplication.and.returnValue(of(underReviewApplication));
    dialog.open.and.returnValue({ afterClosed: () => of(true) } as ReturnType<MatDialog['open']>);

    component.markUnderReview();
    component.markUnderReview();

    expect(component.isActionRunning).toBeTrue();
    expect(applicationService.markUnderReview).toHaveBeenCalledTimes(1);

    transition$.next(underReviewApplication);
    transition$.complete();

    expect(component.isActionRunning).toBeFalse();
    expect(component.application?.status).toBe('UNDER_REVIEW');
    expect(applicationService.getApplication).toHaveBeenCalledWith(7);
    expect(snackBar.open).toHaveBeenCalledWith(
      'La candidature est maintenant en revue.',
      'Fermer',
      { duration: 3500 },
    );
  });

  it('unlocks actions without calling the API when the confirmation is cancelled', () => {
    dialog.open.and.returnValue({ afterClosed: () => of(false) } as ReturnType<MatDialog['open']>);

    component.markUnderReview();

    expect(component.isActionRunning).toBeFalse();
    expect(applicationService.markUnderReview).not.toHaveBeenCalled();
  });

  it('shows the API transition message and unlocks the actions after an error', () => {
    dialog.open.and.returnValue({ afterClosed: () => of(true) } as ReturnType<MatDialog['open']>);
    applicationService.markUnderReview.and.returnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 400,
            error: { non_field_errors: ['Transition invalide de SUBMITTED vers ACCEPTED.'] },
          }),
      ),
    );

    component.markUnderReview();

    expect(component.isActionRunning).toBeFalse();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Transition invalide de SUBMITTED vers ACCEPTED.',
      'Fermer',
      { duration: 5000 },
    );
  });
});
