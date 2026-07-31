import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  BusinessUnit,
  BusinessUnitNeed,
  NeedPriority,
  NeedRequiredLevel,
  NeedStatus,
  NeedType,
} from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuNeedForm } from './bu-need-form';

const businessUnit: BusinessUnit = {
  id: 4,
  name: 'Data',
  code: 'DATA',
  description: '',
  manager: 2,
  manager_email: 'manager@example.com',
  manager_name: 'Manager BU',
  is_active: true,
  created_at: '',
  updated_at: '',
};

const need: BusinessUnitNeed = {
  id: 9,
  business_unit: 4,
  business_unit_name: 'Data',
  title: 'Développeur Angular',
  description: 'Renfort frontend',
  need_type: NeedType.RECRUITMENT_INTERNSHIP,
  need_type_label: 'Recrutement',
  required_skills: 'Angular',
  required_level: NeedRequiredLevel.MID,
  required_level_label: 'Intermédiaire',
  number_of_profiles: 1,
  priority: NeedPriority.HIGH,
  priority_label: 'Haute',
  expected_date: null,
  status: NeedStatus.SUBMITTED,
  status_label: 'Soumis',
  created_by: 2,
  created_by_email: 'manager@example.com',
  created_at: '',
  updated_at: '',
};

describe('BuNeedForm', () => {
  let fixture: ComponentFixture<BuNeedForm>;
  let component: BuNeedForm;
  let service: jasmine.SpyObj<BusinessUnitService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  async function createComponent(needId?: string): Promise<void> {
    service = jasmine.createSpyObj('BusinessUnitService', [
      'createNeed',
      'getBusinessUnits',
      'getMemberships',
      'getNeed',
      'updateNeed',
    ]);
    router = jasmine.createSpyObj('Router', ['navigateByUrl']);
    router.navigateByUrl.and.resolveTo(true);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    service.getBusinessUnits.and.returnValue(of({ count: 1, next: null, previous: null, results: [businessUnit] }));
    service.getMemberships.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    service.getNeed.and.returnValue(of(need));

    await TestBed.configureTestingModule({
      imports: [BuNeedForm],
      providers: [
        { provide: BusinessUnitService, useValue: service },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap(needId ? { needId } : {}) } },
        },
      ],
    });
    TestBed.overrideComponent(BuNeedForm, {
      remove: { imports: [MatSnackBarModule] },
    });
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(BuNeedForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => TestBed.resetTestingModule());

  it('creates a need for the managed Business Unit and returns to the refreshed list', async () => {
    await createComponent();
    expect(component.managedBusinessUnits).toEqual([businessUnit]);
    expect(component.form.controls.business_unit.value).toBe(4);
    expect(fixture.nativeElement.querySelector('form')).not.toBeNull();
    service.createNeed.and.returnValue(of(need));
    component.form.patchValue({ title: 'Développeur Angular', description: 'Renfort frontend' });

    component.save();

    expect(service.createNeed).toHaveBeenCalledWith(jasmine.objectContaining({ business_unit: 4 }));
    expect(snackBar.open).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledOnceWith('/business-units/needs');
    expect(component.isSaving).toBeFalse();
  });

  it('keeps the empty-assignment message and provides a return link', async () => {
    await createComponent();
    service.getBusinessUnits.calls.reset();
    service.getBusinessUnits.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.errorMessage).toContain('Aucune Business Unit active');
    expect(fixture.nativeElement.querySelector('form')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Retour aux besoins');
  });

  it('loads and updates an existing managed need', async () => {
    await createComponent('9');
    service.updateNeed.and.returnValue(of({ ...need, title: 'Nouveau titre' }));
    component.form.controls.title.setValue('Nouveau titre');

    component.save();

    expect(service.getNeed).toHaveBeenCalledOnceWith(9);
    expect(service.updateNeed).toHaveBeenCalledWith(9, jasmine.objectContaining({ title: 'Nouveau titre' }));
  });

  it('does not save a need for a Business Unit outside the managed list', async () => {
    await createComponent();
    component.form.patchValue({ business_unit: 99, title: 'Titre', description: 'Description' });

    component.save();

    expect(service.createNeed).not.toHaveBeenCalled();
    expect(component.errorMessage).toContain('pas accessible');
  });

  it('shows API validation errors and unlocks the form', async () => {
    await createComponent();
    service.createNeed.and.returnValue(throwError(() => ({ error: { title: ['Titre déjà utilisé.'] } })));
    component.form.patchValue({ title: 'Titre', description: 'Description' });

    component.save();

    expect(component.errorMessage).toContain('Titre déjà utilisé.');
    expect(component.isSaving).toBeFalse();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('sends the specific training audience as normalized email values', async () => {
    await createComponent();
    service.createNeed.and.returnValue(of(need));
    component.form.patchValue({
      title: 'Formation Angular',
      description: 'Formation ciblée',
      need_type: NeedType.TRAINING,
      training_audience: 'SPECIFIC',
      specific_recipient_emails: 'one@example.com; two@example.com',
    });

    component.save();

    expect(service.createNeed).toHaveBeenCalledWith(jasmine.objectContaining({
      training_audience: 'SPECIFIC',
      specific_recipient_emails: ['one@example.com', 'two@example.com'],
    }));
  });
});
