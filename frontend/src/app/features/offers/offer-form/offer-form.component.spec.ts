import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { OfferService } from '../../../core/services/offer.service';
import { OfferFormComponent } from './offer-form.component';

describe('OfferFormComponent API errors', () => {
  let fixture: ComponentFixture<OfferFormComponent>;
  let component: OfferFormComponent;
  let offerService: jasmine.SpyObj<OfferService>;

  beforeEach(async () => {
    offerService = jasmine.createSpyObj('OfferService', ['getOffer', 'createOffer', 'updateOffer']);
    await TestBed.configureTestingModule({
      imports: [OfferFormComponent],
      providers: [
        provideNoopAnimations(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null } } } },
        { provide: OfferService, useValue: offerService },
        { provide: BusinessUnitService, useValue: { getBusinessUnits: () => of({ count: 1, results: [{ id: 1, name: 'NetSEC' }] }) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(OfferFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('displays backend date errors on their corresponding controls', () => {
    offerService.createOffer.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 400,
      error: {
        start_date: ["La date n'a pas le bon format."],
        end_date: ['La date de fin est invalide.'],
        application_deadline: ['La date limite est invalide.'],
      },
    })));
    component.form.patchValue({
      title: 'Offre', description: 'Description', business_unit: 1, application_type: 'HIRING',
      start_date: new Date(2027, 0, 1), end_date: new Date(2027, 1, 1), application_deadline: new Date(2026, 11, 1),
    });

    component.onSubmit();

    expect(component.apiDateError('start_date')).toContain("n'a pas le bon format");
    expect(component.apiDateError('end_date')).toContain('fin est invalide');
    expect(component.apiDateError('application_deadline')).toContain('limite est invalide');
    expect(component.form.controls.start_date.touched).toBeTrue();
  });

  it('displays all offer date-picker values in French day/month/year format', () => {
    component.form.patchValue({
      start_date: new Date(2026, 7, 28),
      end_date: new Date(2026, 10, 1),
      application_deadline: new Date(2026, 8, 30),
    });
    fixture.detectChanges();

    const inputValue = (controlName: string) =>
      (fixture.nativeElement.querySelector(`input[formcontrolname="${controlName}"]`) as HTMLInputElement).value;
    expect(inputValue('start_date')).toBe('28/08/2026');
    expect(inputValue('end_date')).toBe('01/11/2026');
    expect(inputValue('application_deadline')).toBe('30/09/2026');
  });
});
