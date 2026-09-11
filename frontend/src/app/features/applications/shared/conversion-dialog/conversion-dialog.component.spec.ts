import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { ApplicationService } from '../../../../core/services/application.service';
import { BusinessUnitService } from '../../../../core/services/business-unit.service';
import {
  ConversionDialogComponent,
  ConversionDialogData,
} from './conversion-dialog.component';

describe('ConversionDialogComponent', () => {
  let fixture: ComponentFixture<ConversionDialogComponent>;
  let component: ConversionDialogComponent;
  let applicationService: jasmine.SpyObj<ApplicationService>;
  let businessUnitService: jasmine.SpyObj<BusinessUnitService>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<ConversionDialogComponent>>;

  const configure = async (conversionType: 'INTERN' | 'EMPLOYEE') => {
    applicationService = jasmine.createSpyObj('ApplicationService', ['convertApplication']);
    businessUnitService = jasmine.createSpyObj('BusinessUnitService', [
      'getBusinessUnits', 'getEligibleSupervisors',
    ]);
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    businessUnitService.getBusinessUnits.and.returnValue(of({
      count: 1, next: null, previous: null,
      results: [{ id: 4, name: 'NetSEC', code: 'NetSEC', is_active: true } as never],
    }));
    businessUnitService.getEligibleSupervisors.and.returnValue(of([
      { id: 8, email: 'supervisor@test.com', full_name: 'Supervisor', role: 'EMPLOYEE', role_label: 'Collaborateur' },
    ]));
    TestBed.configureTestingModule({
      imports: [ConversionDialogComponent],
      providers: [
        provideNoopAnimations(),
        { provide: ApplicationService, useValue: applicationService },
        { provide: BusinessUnitService, useValue: businessUnitService },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {
          applicationId: 7, candidateName: 'Jane Candidate',
          candidateSchool: 'Smart School', conversionType,
        } satisfies ConversionDialogData },
      ],
    });
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(ConversionDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  afterEach(() => TestBed.resetTestingModule());

  it('builds and submits the complete internship payload', async () => {
    await configure('INTERN');
    applicationService.convertApplication.and.returnValue(of({
      detail: 'Conversion réussie.', conversion_type: 'INTERN', profile_id: 11,
      login_email: 'candidate@example.com', credentials_preserved: true,
      application: { id: 7 } as never,
    }));
    component.form.patchValue({
      business_unit: 4, supervisor: 8, school: 'Smart School',
      specialization: 'Cyber', internship_type: 'PFE', paid: true,
      internship_start: '2026-10-01', internship_end: '2027-02-01',
      subject_title: 'SOC',
    });

    component.submit();

    expect(businessUnitService.getEligibleSupervisors).toHaveBeenCalledWith(4);
    expect(applicationService.convertApplication).toHaveBeenCalledWith(7, jasmine.objectContaining({
      conversion_type: 'INTERN', business_unit: 4, supervisor: 8,
      school: 'Smart School', specialization: 'Cyber', paid: true,
    }));
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('submits only collaborator fields for an employee conversion', async () => {
    await configure('EMPLOYEE');
    applicationService.convertApplication.and.returnValue(of({
      detail: 'Conversion réussie.', conversion_type: 'EMPLOYEE', profile_id: 12,
      login_email: 'candidate@example.com', credentials_preserved: true,
      application: { id: 7 } as never,
    }));
    component.form.controls.business_unit.setValue(4);

    component.submit();

    expect(applicationService.convertApplication).toHaveBeenCalledWith(7, {
      conversion_type: 'EMPLOYEE', business_unit: 4,
    });
  });

  it('keeps the dialog open and exposes backend validation errors', async () => {
    await configure('INTERN');
    applicationService.convertApplication.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 400,
      error: { supervisor: ['L’encadrant appartient à une autre BU.'] },
    })));
    component.form.patchValue({ business_unit: 4, supervisor: 8 });

    component.submit();

    expect(component.fieldErrors.supervisor).toContain('autre BU');
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});

