import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { EMPTY, of, Subject, throwError } from 'rxjs';

import { Application } from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';
import { AuthService } from '../../../core/services/auth.service';
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
  status: 'RECEIVED',
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
  const authServiceStub = {
    currentUserSnapshot: {
      id: 99, email: 'admin@test.com', first_name: 'Admin', last_name: '',
      full_name: 'Admin', phone_number: '', role: 'SUPER_ADMIN',
      preferred_language: 'fr',
    },
  };

  beforeEach(async () => {
    applicationService = jasmine.createSpyObj<ApplicationService>('ApplicationService', [
      'getApplication',
      'markUnderReview',
      'matchOffers',
    ]);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    applicationService.getApplication.and.returnValue(of(submittedApplication));
    applicationService.matchOffers.and.returnValue(of({ matches: [] }));

    TestBed.configureTestingModule({
      imports: [ApplicationDetailComponent],
      providers: [
        provideNoopAnimations(),
        { provide: ApplicationService, useValue: applicationService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: MatDialog, useValue: dialog },
        { provide: AuthService, useValue: authServiceStub },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '7' }) } },
        },
      ],
    });
    TestBed.overrideComponent(ApplicationDetailComponent, {
      remove: { imports: [MatDialogModule, MatSnackBarModule] },
      add: {
        providers: [
          { provide: MatSnackBar, useValue: snackBar },
          { provide: MatDialog, useValue: dialog },
        ],
      },
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
            error: { non_field_errors: ['Transition invalide de RECEIVED vers ACCEPTED.'] },
          }),
      ),
    );

    component.markUnderReview();

    expect(component.isActionRunning).toBeFalse();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Transition invalide de RECEIVED vers ACCEPTED.',
      'Fermer',
      { duration: 5000 },
    );
  });

  it('always stops the initial loader when the detail request completes', () => {
    applicationService.getApplication.and.returnValue(EMPTY);

    component.loadApplication();

    expect(component.isLoading).toBeFalse();
  });

  it('shows both conversion actions only to a Super Admin for an accepted candidate', () => {
    component.application = {
      ...submittedApplication, status: 'ACCEPTED', conversion: null,
    };
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Convertir en stagiaire');
    expect(text).toContain('Convertir en collaborateur');

    authServiceStub.currentUserSnapshot.role = 'HR';
    fixture.detectChanges();
    const hrText = fixture.nativeElement.textContent as string;
    expect(hrText).not.toContain('Convertir en stagiaire');
    expect(hrText).not.toContain('Convertir en collaborateur');
  });

  it('hides conversion actions after a conversion is recorded', () => {
    component.application = {
      ...submittedApplication,
      status: 'ACCEPTED',
      candidate_profile: { ...submittedApplication.candidate_profile, role: 'INTERN' },
      conversion: { type: 'INTERN', profile_id: 12 },
    };
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Convertir en stagiaire');
  });

  it('opens the selected conversion form and refreshes the application after success', () => {
    authServiceStub.currentUserSnapshot.role = 'SUPER_ADMIN';
    const accepted = { ...submittedApplication, status: 'ACCEPTED' as const, conversion: null };
    const converted = {
      ...accepted,
      candidate_profile: { ...accepted.candidate_profile, role: 'EMPLOYEE' as const },
      conversion: { type: 'EMPLOYEE' as const, profile_id: 22 },
    };
    component.application = accepted;
    applicationService.getApplication.and.returnValue(of(converted));
    dialog.open.and.returnValue({ afterClosed: () => of({
      detail: 'Candidat converti avec succès.', conversion_type: 'EMPLOYEE',
      profile_id: 22, login_email: 'candidate@example.com',
      credentials_preserved: true, application: converted,
    }) } as ReturnType<MatDialog['open']>);

    component.openConversion('EMPLOYEE');

    expect(dialog.open).toHaveBeenCalled();
    expect(applicationService.getApplication).toHaveBeenCalledWith(7);
    expect(component.application?.conversion?.type).toBe('EMPLOYEE');
    expect(snackBar.open).toHaveBeenCalledWith(
      'Candidat converti avec succès.', 'Fermer', { duration: 3500 },
    );
  });
});
