import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';


import { ApplicationService } from '../../../core/services/application.service';
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
          useValue: {},
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
    expect(component.generalError).toBe('Le dossier ne peut pas être traité.');
  });
});
