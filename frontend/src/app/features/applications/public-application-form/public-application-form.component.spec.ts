import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatStepper } from '@angular/material/stepper';
import { of, throwError } from 'rxjs';


import { ApplicationService } from '../../../core/services/application.service';
import { OfferService } from '../../../core/services/offer.service';
import { PublicApplicationFormComponent } from './public-application-form.component';

describe('PublicApplicationFormComponent', () => {
  let component: PublicApplicationFormComponent;
  let fixture: ComponentFixture<PublicApplicationFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PublicApplicationFormComponent],
      providers: [
        provideNoopAnimations(),
        {
          provide: ApplicationService,
          useValue: {
            submitPublicApplication: jasmine.createSpy().and.returnValue(of({})),
            previewCV: jasmine.createSpy().and.returnValue(of({
              id: 0,
              first_name: 'Jane',
              last_name: 'Doe',
              full_name: 'Jane Doe',
              email: 'jane@example.com',
              phone: '+212600000000',
              location: 'Casablanca',
              skills: ['Python', 'Django'],
              experiences: [{
                position: 'Backend Developer', company: 'Acme', start_date: '2022', end_date: '2024',
                duration: '2 ans', description: 'Conception des API\nMaintenance | documentation',
              }],
              education: [{ title: 'Master Informatique', institution: 'ENSA', start_date: '', end_date: '' }],
              diplomas: ['Master Informatique'],
              companies: [],
              positions: [],
              languages: ['Français'],
              certifications: [],
              extraction_method: 'DOCX',
              extraction_warnings: [],
              extractor_version: 'test',
              human_validated: false,
              validated_at: null,
            })),
          },
        },
        {
          provide: OfferService,
          useValue: {
            getOffers: jasmine.createSpy().and.returnValue(of({ results: [] })),
          },
        },
        {
          provide: Router,
          useValue: {
            navigateByUrl: jasmine.createSpy().and.returnValue(Promise.resolve(true)),
          },
        },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: { get: (key: string) => key === 'offer' ? '2' : null } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PublicApplicationFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('rejects submission when required documents are missing', () => {
    component.submit();

    expect(component.fileErrors.cv).toBe('Le CV est obligatoire.');
    expect(component.fileErrors.cover).toBe('La lettre de motivation est obligatoire.');
    expect(component.fileErrors.photo).toBe('La photo personnelle est obligatoire.');
  });

  it('requires a custom study level only when OTHER is selected', () => {
    component.form.controls.academic.controls.study_level.setValue('OTHER');
    component.form.controls.academic.controls.study_level_other.markAsTouched();

    expect(component.form.controls.academic.controls.study_level_other.hasError('required')).toBeTrue();

    component.form.controls.academic.controls.study_level_other.setValue('Formation professionnelle');
    expect(component.form.controls.academic.controls.study_level_other.valid).toBeTrue();

    component.form.controls.academic.controls.study_level.setValue('MASTER');
    expect(component.form.controls.academic.controls.study_level_other.value).toBe('');
    expect(component.form.controls.academic.controls.study_level_other.hasError('required')).toBeFalse();
  });

  it('rejects a file with an unauthorized MIME type', async () => {
    const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'cv.pdf', {
      type: 'text/plain',
    });
    const input = {
      files: [file],
      value: 'cv.pdf',
    };

    await component.onFileSelected({ target: input } as unknown as Event, 'cv');

    expect(component.cvFile).toBeNull();
    expect(component.fileErrors.cv).toBe('Type de fichier non autorisé.');
  });

  it('analyzes the CV first and prefills candidate information', async () => {
    const file = new File([new Uint8Array([0x50, 0x4b, 0x03, 0x04])], 'cv.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    await component.onFileSelected({ target: { files: [file], value: 'cv.docx' } } as unknown as Event, 'cv');

    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    expect(applicationService.previewCV).toHaveBeenCalledTimes(1);
    expect(component.canContinueAfterCV()).toBeTrue();
    expect(component.form.controls.personal.value).toEqual(jasmine.objectContaining({
      first_name: 'Jane',
      last_name: 'Doe',
      email: 'jane@example.com',
      phone_number: '+212600000000',
    }));
    expect(component.form.controls.academic.value).toEqual(jasmine.objectContaining({
      current_school: 'ENSA',
      study_field: 'Master Informatique',
      study_level: 'MASTER',
    }));
    expect(component.cvReviewForm.controls.skills.value).toBe('Python\nDjango');
    expect(component.cvReviewForm.controls.experiences.valid).toBeTrue();
    expect(component.cvReviewForm.controls.experiences.value.split('\n').length).toBe(1);
  });

  it('shows a safe French message when CV preview is throttled', async () => {
    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    applicationService.previewCV.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 429,
      error: { detail: 'Request was throttled. Expected available in 3599 seconds.' },
    })));
    const file = new File([new Uint8Array([0x50, 0x4b, 0x03, 0x04])], 'cv.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    await component.onFileSelected({ target: { files: [file], value: 'cv.docx' } } as unknown as Event, 'cv');

    expect(applicationService.previewCV).toHaveBeenCalledTimes(1);
    expect(component.fileErrors.cv).toBe(
      'Trop de tentatives d’analyse ont été effectuées. Veuillez réessayer dans quelques instants.',
    );
  });

  it('maps Django field errors to the matching fields and preserves general errors', () => {
    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    component.form.patchValue({
      personal: {
        email: 'candidate@example.com',
        password: 'StrongPass123!',
        first_name: 'Jane',
        last_name: 'Candidate',
        phone_number: '+212600000000',
      },
      academic: {
        current_school: 'Smart University',
        study_level: 'MASTER',
        study_field: 'Développement logiciel',
      },
      professional: {
        application_type: 'PFA_INTERNSHIP',
      }
    });
    component.cvFile = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' });
    component.coverLetterFile = new File(['%PDF'], 'letter.pdf', { type: 'application/pdf' });
    component.personalPhotoFile = new File(['photo'], 'photo.jpg', { type: 'image/jpeg' });
    applicationService.submitPublicApplication.and.returnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 400,
            error: {
              email: ['Un compte existe déjà avec cet email.'],
              phone_number: ['Numéro de téléphone invalide.'],
              cv: ['Le CV ne peut pas être lu.'],
              cover_letter: ['La lettre est obligatoire.'],
              personal_photo: ['La photo est obligatoire.'],
              non_field_errors: ['Le dossier ne peut pas être traité.'],
            },
          }),
      ),
    );

    component.submit();

    expect(component.apiError('email')).toBe('Un compte existe déjà avec cet email.');
    expect(component.apiError('phone_number')).toBe('Numéro de téléphone invalide.');
    expect(component.fileErrors.cv).toBe('Le CV ne peut pas être lu.');
    expect(component.fileErrors.cover).toBe('La lettre est obligatoire.');
    expect(component.fileErrors.photo).toBe('La photo est obligatoire.');
    expect(component.generalError).toContain('Un compte existe déjà avec cet email.');
    expect(component.generalError).toContain('Le dossier ne peut pas être traité.');
  });

  it('validates and maps an error to the exact experience position line', () => {
    component.cvReviewForm.controls.experiences.setValue(`${'x'.repeat(256)} | Acme | 2022 | 2024 | 2 ans | API`);
    expect(component.cvReviewForm.controls.experiences.hasError('experiencePositions')).toBeTrue();

    (component as any).applyApiErrors(new HttpErrorResponse({
      status: 400,
      error: { experiences: [{ position: ['Ensure this field has no more than 255 characters.'] }] },
    }));

    expect(component.experiencePositionErrors[0]).toBe(
      'Ensure this field has no more than 255 characters.',
    );
  });

  it('sends public-submit for a valid completed application', () => {
    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    component.form.patchValue({
      personal: { email: 'valid@example.com', password: 'StrongPass123!', first_name: 'Jane', last_name: 'Doe', phone_number: '+212600000000' },
      academic: { current_school: 'ENSA', study_level: 'MASTER', study_field: 'Informatique' },
      professional: { application_type: 'HIRING' },
    });
    component.cvFile = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' });
    component.coverLetterFile = new File(['%PDF'], 'letter.pdf', { type: 'application/pdf' });
    component.personalPhotoFile = new File(['photo'], 'photo.jpg', { type: 'image/jpeg' });
    component.cvAnalysis = {} as any;
    component.cvReviewForm.controls.experiences.setValue('Backend Developer | Acme | 2022 | 2024 | 2 ans | API internes');

    component.submit();

    expect(applicationService.submitPublicApplication).toHaveBeenCalledTimes(1);
    const payload = applicationService.submitPublicApplication.calls.mostRecent().args[0];
    expect(payload instanceof FormData).toBeTrue();
    expect(payload.get('offer')).toBe('2');
  });

  it('shows the exact experience position error and returns to verification', () => {
    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    component.form.patchValue({
      personal: { email: 'valid@example.com', password: 'StrongPass123!', first_name: 'Jane', last_name: 'Doe', phone_number: '+212600000000' },
      academic: { current_school: 'ENSA', study_level: 'MASTER', study_field: 'Informatique' },
      professional: { application_type: 'HIRING' },
    });
    component.cvFile = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' });
    component.coverLetterFile = new File(['%PDF'], 'letter.pdf', { type: 'application/pdf' });
    component.personalPhotoFile = new File(['photo'], 'photo.jpg', { type: 'image/jpeg' });
    component.cvReviewForm.controls.experiences.setValue(`${'x'.repeat(256)} | Acme | 2022 | 2024 | 2 ans | API`);
    const stepper = { selectedIndex: 4 } as MatStepper;

    component.submit(stepper);

    expect(applicationService.submitPublicApplication).not.toHaveBeenCalled();
    expect(stepper.selectedIndex).toBe(1);
    expect(component.generalError).toContain('poste de l’expérience');
    expect(component.generalError).toContain('ligne 1');
  });

  it('reports a hidden invalid control and returns to its step', () => {
    const applicationService = TestBed.inject(ApplicationService) as jasmine.SpyObj<ApplicationService>;
    component.form.patchValue({
      personal: { email: 'valid@example.com', password: 'StrongPass123!', first_name: 'Jane', last_name: 'Doe', phone_number: '+212600000000' },
      academic: { current_school: 'ENSA', study_level: 'MASTER', study_field: 'Informatique' },
      professional: { application_type: '' },
    });
    component.cvFile = new File(['%PDF'], 'cv.pdf', { type: 'application/pdf' });
    component.coverLetterFile = new File(['%PDF'], 'letter.pdf', { type: 'application/pdf' });
    component.personalPhotoFile = new File(['photo'], 'photo.jpg', { type: 'image/jpeg' });
    const stepper = { selectedIndex: 4 } as MatStepper;

    component.submit(stepper);

    expect(applicationService.submitPublicApplication).not.toHaveBeenCalled();
    expect(stepper.selectedIndex).toBe(2);
    expect(component.generalError).toContain('type de candidature');
  });
});
