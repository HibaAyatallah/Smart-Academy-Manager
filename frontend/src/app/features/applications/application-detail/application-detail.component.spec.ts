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
      'reviewMatch',
    ]);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    applicationService.getApplication.and.returnValue(of(submittedApplication));
    applicationService.matchOffers.and.returnValue(of({ matches: [], training_recommendations: [], recommendations_stale: false }));

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

  it('displays hybrid semantic scoring, recommendations and human review', () => {
    const match = {
      id: 12, application: 7, offer: 3, offer_title: 'Backend', candidate_name: 'Jane Candidate',
      score: 86, matched_skills: ['Python'], missing_skills: ['Docker'], additional_skills: [],
      score_breakdown: {
        label: 'Strong match',
        skills: {score: 80, weight: 50, available: true},
        experience: {score: null, weight: 25, available: false},
        education: {score: 100, weight: 15, available: true},
        semantic: {score: 91, weight: 30, available: true},
      },
      candidate_summary: 'Profil cohérent.', explanation: 'Score hybride explicable.',
      algorithm_version: 'hybrid-v1', semantic_score: 91,
      semantic_model: 'ollama:bge-m3@bge-m3-v1/1024d', human_decision: 'PENDING' as const,
      reviewed_at: null, created_at: '', updated_at: '', is_stale: false,
    };
    applicationService.matchOffers.and.returnValue(of({
      matches: [match],
      training_recommendations: [{
        id: 5, training: 8, training_title: 'Docker essentiel', score: 100,
        skill_gaps: ['Docker'], explanation: 'Couvre Docker.', human_decision: 'PENDING',
      }],
      recommendations_stale: false,
    }));
    applicationService.reviewMatch.and.returnValue(of({id: 12, human_decision: 'APPROVED', reviewed_at: '2026-09-12T10:00:00Z'}));
    component.application = {...submittedApplication, offer: 3};

    component.loadAIMatch(7);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Similarité sémantique');
    expect(text).toContain('91%');
    expect(text).toContain('Docker essentiel');
    expect(text).toContain('Score hybride');

    component.reviewAIMatch('APPROVED');
    expect(applicationService.reviewMatch).toHaveBeenCalledOnceWith(7, 12, 'APPROVED');
    expect(component.aiMatch?.human_decision).toBe('APPROVED');
  });

  it('hides stale scores and recommendations', () => {
    applicationService.matchOffers.and.returnValue(of({
      matches: [{
        id: 12, application: 7, offer: 3, offer_title: 'Backend', candidate_name: 'Jane Candidate',
        score: null, matched_skills: [], missing_skills: [], additional_skills: [], score_breakdown: null,
        candidate_summary: null, explanation: 'Ce résultat est obsolète.', algorithm_version: 'hybrid-v1',
        semantic_score: null, semantic_model: 'ollama:bge-m3@bge-m3-v1/1024d',
        human_decision: 'PENDING', reviewed_at: null, created_at: '', updated_at: '', is_stale: true,
      }],
      training_recommendations: [], recommendations_stale: true,
    }));
    component.application = {...submittedApplication, offer: 3};

    component.loadAIMatch(7);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('matching est obsolète');
    expect(text).toContain('recommandations précédentes sont masquées');
    expect(text).not.toContain('Valider l’aide IA');
  });
});
