import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuCreateDialog } from './bu-create-dialog';

describe('BuCreateDialog', () => {
  let fixture: ComponentFixture<BuCreateDialog>;
  let component: BuCreateDialog;
  let service: jasmine.SpyObj<BusinessUnitService>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<BuCreateDialog>>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getUsers', 'createBusinessUnit']);
    service.getUsers.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    await TestBed.configureTestingModule({
      imports: [BuCreateDialog],
      providers: [
        provideNoopAnimations(),
        { provide: BusinessUnitService, useValue: service },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BuCreateDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates a valid Business Unit and closes with the result', () => {
    const created = { id: 9, name: 'Data & AI', code: 'DATA_AI', is_active: true } as any;
    service.createBusinessUnit.and.returnValue(of(created));
    component.form.setValue({ name: 'Data & AI', code: 'DATA_AI', manager: null, is_active: true });

    component.submit();

    expect(service.createBusinessUnit).toHaveBeenCalledWith(component.form.getRawValue());
    expect(dialogRef.close).toHaveBeenCalledWith(created);
  });

  it('shows duplicate name and code errors returned by the backend', () => {
    service.createBusinessUnit.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 400,
      error: { name: ['Une Business Unit avec ce nom existe déjà.'], code: ['Une Business Unit avec ce code existe déjà.'] },
    })));
    component.form.setValue({ name: 'NetSEC', code: 'NetSEC', manager: null, is_active: true });

    component.submit();

    expect(component.fieldErrors.name).toContain('existe déjà');
    expect(component.fieldErrors.code).toContain('existe déjà');
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
